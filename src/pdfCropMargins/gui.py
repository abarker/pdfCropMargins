# -*- coding: utf-8 -*-
"""

Code to create and execute the GUI when that option is selected.

=========================================================================

This code is heavily modified from example/demo code found here:
https://github.com/PySimpleGUI/PySimpleGUI/blob/master/DemoPrograms/Demo_PDF_Viewer.py
Below is from original module docstring:

    @created: 2018-08-19 18:00:00
    @author: (c) 2018-2019 Jorj X. McKie
    Display a PyMuPDF Document using Tkinter

    License:
    --------
    GNU GPL V3+

Copyright (C) 2019 Allen Barker (Allen.L.Barker@gmail.com)
Source code site: https://github.com/abarker/pdfCropMargins

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

# TODO: Consider setting up so if no input file argument and the gui is used then
# the file chooser will pop up.

# TODO: Maybe use spinner for orderStat, checkbox for uniform and samepagesize.
# Maybe not.

from __future__ import print_function, absolute_import

import sys
import os
import warnings
from . import __version__
from . import external_program_calls as ex

try:
    with warnings.catch_warnings():
        #warnings.filterwarnings("ignore",category=DeprecationWarning)
        import fitz
    if not list(map(int, fitz.VersionBind.split("."))) >= [1, 14, 5]:
        raise ImportError
    if not ex.python_version[0] == "2":
        import PySimpleGUI as sg
        import tkinter as tk
    else:
        import PySimpleGUI27 as sg
        import Tkinter as tk
except ImportError:
    print("\nThe GUI feature requires Tkinter, pySimpleGUI, and PyMuPDF at least v1.14.5."
          "\nIf installing via pip, use the optional-feature install:"
          "\n   pip install pdfCropMargins[gui]", file=sys.stderr)
    raise

from .main_pdfCropMargins import (process_pdf_file, parse_page_range_specifiers,
                                  parse_page_ratio_argument)
from .external_program_calls import cleanup_and_exit

# Look and feel.
#print(sg.ListOfLookAndFeelValues())
#print(sg.LOOK_AND_FEEL_TABLE)
#sg.ChangeLookAndFeel("SandyBeach")

#
# Helper functions.
#

def get_filename():
    """Get the filename of the PDF file via GUI if one was not passed in."""
    fname = sg.PopupGetFile("Select file and filetype to open:",
                            title="pdfCropMargins: Document Browser",
                            file_types=[ # Only PDF files.
                                          ("PDF Files", "*.pdf"),
                                       ],
                            )
    if not fname:
        sg.Popup("Cancelling:", "No filename supplied")
        raise PdfCropMarginsError("Cancelled: no filename supplied")

    return fname

def open_document(doc_fname):
    """Return the document opened by fitz (PyMuPDF)."""
    # TODO: Move the get_filename call to main_pdfCropMargins or
    # similar if actually used.
    if not doc_fname:
        doc_fname = get_filename()
    try:
        document = fitz.open(doc_fname)
    except RuntimeError:
        print("\nError in pdfCropMargins: The PyMuPDF program could not read"
              " the document\n   '{}'\nin order to display it in the GUI.   If you have"
              " Ghostscript installed\nconsider running pdfCropMargins with the"
              " '--gsFix' option to attempt to repair it."
              .format(doc_fname), file=sys.stderr)
        ex.cleanup_and_exit(1)
    page_count = len(document)
    return document, page_count

def get_page(page_num, page_display_list_cache, document, window_size, zoom=False):
    """Return a `tkinter.PhotoImage` or a PNG image for a document page number.
    - The `page_num` argument is a 0-based page number.
    - The `zoom` argument is the top-left of old clip rect, and one of -1, 0,
      +1 for dim. x or y to indicate the arrow key pressed.
    - The `max_size` argument is the (width, height) of available image area.
      """
    zoom_x = 1
    zoom_y = 1
    scale = fitz.Matrix(zoom_x, zoom_y)
    page_display_list = page_display_list_cache[page_num]
    if not page_display_list:  # Create if not yet there.
        page_display_list_cache[page_num] = document[page_num].getDisplayList()
        page_display_list = page_display_list_cache[page_num]

    rect = page_display_list.rect  # The page rectangle.
    clip = rect

    # Make sure that the image will fits the screen.
    zoom_0 = 1
    if window_size:
        zoom_0 = min(1, window_size[0] / rect.width, window_size[1] / rect.height)
        if zoom_0 == 1:
            zoom_0 = min(window_size[0] / rect.width, window_size[1] / rect.height)
    mat_0 = fitz.Matrix(zoom_0, zoom_0)

    if not zoom:  # Show the total page.
        pixmap = page_display_list.getPixmap(matrix=mat_0, alpha=False)
    else:
        w2 = rect.width / 2  # we need these ...
        h2 = rect.height / 2  # a few times
        clip = rect * 0.5  # clip rect size is a quarter page
        tl = zoom[0]  # old top-left
        tl.x += zoom[1] * (w2 / 2)  # adjust top-left ...
        tl.x = max(0, tl.x)  # according to ...
        tl.x = min(w2, tl.x)  # arrow key ...
        tl.y += zoom[2] * (h2 / 2)  # provided, but ...
        tl.y = max(0, tl.y)  # stay within ...
        tl.y = min(h2, tl.y)  # the page rect
        clip = fitz.Rect(tl, tl.x + w2, tl.y + h2)

        # Clip rect is ready, now fill it.
        mat = mat_0 * fitz.Matrix(2, 2)  # The zoom matrix.
        pixmap = page_display_list.getPixmap(alpha=False, matrix=mat, clip=clip)

    image_ppm = pixmap.getImageData("ppm")  # Make PPM image from pixmap for tkinter.
    return image_ppm, clip.tl  # Return image, clip position.

def get_window_size():
    """Get physical screen dimension to determine the page image max size."""
    root = tk.Tk()
    width = root.winfo_screenwidth() - 20
    height = root.winfo_screenheight() - 135
    root.destroy()
    return width, height

def get_help_text_string_for_tooltip(cmd_parser, option_string):
    """Extract the help message for an option from an argparse command parser.
    This gets the argparse help string to use as a tooltip."""
    import textwrap
    wrapper = textwrap.TextWrapper(initial_indent="", subsequent_indent="", width=45)
    for a in cmd_parser._actions:
        if "--" + option_string in a.option_strings:
            help_text = a.help
            option_list = a.option_strings
            break
    else:
        return None
    help_text = textwrap.dedent(help_text)
    formatted_para = wrapper.fill(help_text)
    combined_para = " ".join(option_list) + "\n\n" + formatted_para
    combined_para = combined_para.replace("^^n", "\n")
    return combined_para

#
# Helper functions for updating the values of elements.
#

def call_all_update_funs(update_funs, values_dict):
    """Call all the functions."""
    for f in update_funs:
        f(values_dict)

def to_float_or_NA(value):
    """Convert to float unless the value is 'N/A', which is left unchanged."""
    if value == "N/A":
        return "N/A"
    else:
        return float(value)

def to_int_or_NA(value):
    """Convert to float unless the value is 'N/A', which is left unchanged."""
    if value == "N/A":
        return "N/A"
    else:
        return int(value)

def str_to_bool(string):
    """Convert a string "True" or "False" to the boolean True or False, respectively."""
    if string == "True":
        return True
    elif string == "False":
        return False
    else:
        print("Error in pdfCropMargins: String cannot be converted to bool.",
              file=sys.stderr)
        ex.cleanup_and_exit(1)

def update_value_and_return_it(input_text_element, value=None, fun_to_apply=None):
    """
    1) Get the text in the `InputText` element `input_text_element`.
    2) Apply the function `fun_to_apply` to it (if one is passed in).
    3) Update the text back to the new value.

    If `value` is passed in it will be used in place of the text from step 1)."""
    if value is None:
        value = input_text_element.Get()
    if fun_to_apply:
        value = fun_to_apply(value)
    input_text_element.Update(value)
    return value

def update_combo_box(values_dict, element, element_key, args, attr, fun_to_apply):
    """Update a non-paired, independent option like `uniform`.  Function `fun_to_apply`
    is applied to the GUI value to convert it to the type `args` expects."""
    if values_dict is None:
        return
    element_value = values_dict[element_key]
    element_value = fun_to_apply(element_value)
    element.Update(str(element_value))
    setattr(args, attr, element_value)

def update_4_values(element_list, attr, args_dict, values_dict, value_type=float):
    """Update four values from a 4-value argument to argparse."""
    args_attr = args_dict[attr]

    def update_all_from_args_dict():
        for i in [0,1,2,3]:
            update_value_and_return_it(element_list[i], value=args_attr[i])

    try:
        element_text4 = [str(value_type(element_list[i].Get())) for i in [0,1,2,3]]
    except ValueError:
        update_all_from_args_dict() # Replace bad text with saved version.
        return

    for i in [0,1,2,3]:
        args_attr[i] = update_value_and_return_it(element_list[i],
                                                    fun_to_apply=value_type)

    # Update all, to convert forms like 5 to 5.0 (which were equal above).
    update_all_from_args_dict()

def update_paired_1_and_4_values(element, element_list4, attr, attr4, args_dict,
                                 values_dict, value_type=to_float_or_NA,
                                 value_type4=float):
    """Update all the value for pairs such as `percentRetain` and
    `percentRetain4`, keeping the versions with one vs. four arguments
    synchronized."""
    args_attr = args_dict[attr]
    args_attr4 = args_dict[attr4]

    def update_all_from_args_dict():
        update_value_and_return_it(element, value=args_attr[0])
        for i in [0,1,2,3]:
            update_value_and_return_it(element_list4[i], value=args_attr4[i])

    try:
        element_text = str(value_type(element.Get()))
        #element_text = str(value_type(values_dict[attr])) # Also works.
        element_text4 = [str(value_type4(element_list4[i].Get())) for i in [0,1,2,3]]
    except ValueError:
        update_all_from_args_dict() # Replace bad text with saved version.
        return
    # See if the element value changed.
    if value_type(element_text) != args_attr[0] and element_text != "N/A":
        args_attr[0] = update_value_and_return_it(element, fun_to_apply=value_type)
        for i in [0,1,2,3]:
            args_attr4[i] = update_value_and_return_it(element_list4[i],
                                                       value=args_attr[0])

    # See if any of the element_list4 values changed.
    elif any(value_type4(element_text4[i]) != args_attr4[i] for i in [0,1,2,3]):
        for i in [0,1,2,3]:
            args_attr4[i] = update_value_and_return_it(element_list4[i],
                                                       fun_to_apply=value_type4)
        if len(set(args_attr4)) == 1: # All are the same value.
            args_attr[0] = update_value_and_return_it(element, value=args_attr4[0])
        else:
            args_attr[0] = update_value_and_return_it(element, value="N/A")

    # Update all, to convert forms like 5 to 5.0 (which were equal above).
    update_all_from_args_dict()

#
# The main function with the event loop.
#

def create_gui(input_doc_fname, fixed_input_doc_fname, output_doc_fname,
               cmd_parser, parsed_args):
    """Create a GUI for running pdfCropMargins with parsed arguments `parsed_args`
    on the PDF file named `pdf_filename`"""
    args = parsed_args
    args_dict = {} # Dict for holding "real" values backing the GUI element values.

    ##
    ## Set up the document and window.
    ##

    document, page_count = open_document(fixed_input_doc_fname)
    cur_page = 0

    window_title = "pdfCropMargins: {}".format(os.path.basename(input_doc_fname))
    window_size = get_window_size()
    size_for_full_app = (0.65*window_size[0], window_size[1]) # Reduce max width.

    window = sg.Window(title=window_title, return_keyboard_events=True, location=(0, 0),
                       use_default_focus=False)
    # On tooltips done by pySimpleGUI in tkinter, it seems you have to move pointer
    # left over the text to make them appear...
    sg.SetOptions(tooltip_time=500)

    # Allocate storage for caching page display lists.
    page_display_list_cache = [None] * page_count

    data, clip_pos = get_page(cur_page,  # Read first page.
                              page_display_list_cache,
                              document,
                              window_size=size_for_full_app,  # image max dim
                              zoom=False,  # Not zooming yet.
                              )

    image_element = sg.Image(data=data)  # make image element

    update_funs = [] # A list of all the updating functions (defined below).

    ##
    ## Code for handling page numbers.
    ##

    input_text_page_num = sg.InputText(str(cur_page + 1), size=(5, 1),
                                       do_not_clear=True, key="PageNumber")
    text_page_num = sg.Text("Page:")

    def update_page_number(cur_page, page_count, is_page_mod_key, btn,
                           input_text_element):
        cur_page = max(cur_page, 0)
        cur_page = min(cur_page, page_count-1)
        # Update page number field.
        if is_page_mod_key(btn):
            input_text_element.Update(str(cur_page + 1))
        return cur_page

    ##
    ## Code for percentRetain options.
    ##

    args_dict["percentRetain"] = args.percentRetain
    if len(set(args.percentRetain4)) != 1: # Set initial value if all the same.
        args_dict["percentRetain"] = ["N/A"]
    text_percentRetain = sg.Text("percentRetain",
                      tooltip=get_help_text_string_for_tooltip(cmd_parser, "percentRetain"))
    input_text_percentRetain = sg.InputText(args_dict["percentRetain"][0],
                                 size=(5, 1), do_not_clear=True, key="percentRetain")

    # Code for percentRetain4.
    args_dict["percentRetain4"] = args.percentRetain4
    text_percentRetain4 = sg.Text("percentRetain4",
                      tooltip=get_help_text_string_for_tooltip(cmd_parser, "percentRetain4"))
    input_text_percentRetain4 = [sg.InputText(args_dict["percentRetain4"][i], size=(5, 1),
                                 do_not_clear=True, key="percentRetain4_{}".format(i))
                                 for i in [0,1,2,3]]

    def update_percentRetain_values(values_dict):
        """Update both the percentRetain value and the percentRetain4 values."""
        update_paired_1_and_4_values(input_text_percentRetain,
                    input_text_percentRetain4, "percentRetain", "percentRetain4", args_dict, values_dict)
        # Copy backing values to the actual args object.
        args.percentRetain = args_dict["percentRetain"]
        args.percentRetain4 = args_dict["percentRetain4"]

    update_funs.append(update_percentRetain_values)

    ##
    ## Code for absoluteOffset options.
    ##

    args_dict["absoluteOffset"] = args.absoluteOffset
    if len(set(args.absoluteOffset4)) != 1: # Set initial value if all the same.
        args_dict["absoluteOffset"] = ["N/A"]
    text_absoluteOffset = sg.Text("absoluteOffset",
                      tooltip=get_help_text_string_for_tooltip(cmd_parser, "absoluteOffset"))
    input_text_absoluteOffset = sg.InputText(args_dict["absoluteOffset"][0],
                                 size=(5, 1), do_not_clear=True, key="absoluteOffset")

    # Code for absoluteOffset4.
    args_dict["absoluteOffset4"] = args.absoluteOffset4
    text_absoluteOffset4 = sg.Text("absoluteOffset4",
                      tooltip=get_help_text_string_for_tooltip(cmd_parser, "absoluteOffset4"))
    input_text_absoluteOffset4 = [sg.InputText(args_dict["absoluteOffset4"][i], size=(5, 1),
                                 do_not_clear=True, key="absoluteOffset4_{}".format(i))
                                 for i in [0,1,2,3]]

    def update_absoluteOffset_values(values_dict):
        """Update both the absoluteOffset value and the absoluteOffset4 values."""
        update_paired_1_and_4_values(input_text_absoluteOffset,
                    input_text_absoluteOffset4, "absoluteOffset", "absoluteOffset4", args_dict, values_dict)
        # Copy backing values to the actual args object.
        args.absoluteOffset = args_dict["absoluteOffset"]
        args.absoluteOffset4 = args_dict["absoluteOffset4"]

    update_funs.append(update_absoluteOffset_values)

    ##
    ## Code for uniformOrderStat options.
    ##

    if args.uniformOrderStat:
        args_dict["uniformOrderStat"] = args.uniformOrderStat
    else:
        args_dict["uniformOrderStat"] = [0]
    if args.uniformOrderStat4:
        args_dict["uniformOrderStat4"] = args.uniformOrderStat4
        if len(set(args.uniformOrderStat4)) != 1: # Set initial value if all the same.
            args_dict["uniformOrderStat"] = [0]
        else:
            args_dict["uniformOrderStat"] = [args.uniformOrderStat4[0]]
    elif args.uniformOrderStat:
        args_dict["uniformOrderStat4"] = [args.uniformOrderStat[0]] * 4
    else:
        args_dict["uniformOrderStat4"] = [0] * 4
    text_uniformOrderStat = sg.Text("uniformOrderStat",
                      tooltip=get_help_text_string_for_tooltip(cmd_parser, "uniformOrderStat"))
    input_text_uniformOrderStat = sg.InputText(args_dict["uniformOrderStat"][0],
                                 size=(5, 1), do_not_clear=True, key="uniformOrderStat")

    # Code for uniformOrderStat4.
    text_uniformOrderStat4 = sg.Text("uniformOrderStat4",
                      tooltip=get_help_text_string_for_tooltip(cmd_parser, "uniformOrderStat4"))
    input_text_uniformOrderStat4 = [sg.InputText(args_dict["uniformOrderStat4"][i], size=(5, 1),
                                 do_not_clear=True, key="uniformOrderStat4_{}".format(i))
                                 for i in [0,1,2,3]]

    def update_uniformOrderStat_values(values_dict):
        """Update both the uniformOrderStat value and the uniformOrderStat4 values."""
        update_paired_1_and_4_values(input_text_uniformOrderStat,
              input_text_uniformOrderStat4, "uniformOrderStat",
              "uniformOrderStat4", args_dict, values_dict,
              value_type=to_int_or_NA, value_type4=int)
        # Copy backing values to the actual args object.
        args.uniformOrderStat = [] # Not needed with uniformOrderStat4 always set.
        if all(i == 0 for i in args_dict["uniformOrderStat4"]):
            args.uniformOrderStat4 = [] # Need to empty it, since it implies uniform option.
        else:
            args.uniformOrderStat4 = args_dict["uniformOrderStat4"]

    update_funs.append(update_uniformOrderStat_values)

    ##
    ## Code for uniform.
    ##

    text_uniform = sg.Text("uniform", pad=((0,20), None),
                      tooltip=get_help_text_string_for_tooltip(cmd_parser, "uniform"))

    # BUG in PySimpleGUI?  Default values not set unless they are strings!
    combo_box_uniform = sg.Combo(["True", "False"], readonly=True, default_value=str(args.uniform),
                                       size=(5, 1), key="uniform", enable_events=True)

    def update_uniform(values_dict):
        """Update the uniform values."""
        update_combo_box(values_dict, combo_box_uniform, "uniform", args, "uniform",
                        fun_to_apply=str_to_bool)

    update_funs.append(update_uniform)

    ##
    ## Code for samePageSize.
    ##

    text_samePageSize = sg.Text("samePageSize",
                      tooltip=get_help_text_string_for_tooltip(cmd_parser, "samePageSize"))

    combo_box_samePageSize = sg.Combo(["True", "False"], readonly=True,
                                         default_value=str(args.samePageSize), size=(5, 1),
                                         key="samePageSize", enable_events=True)

    def update_samePageSize(values_dict):
        """Update the samePageSize values."""
        update_combo_box(values_dict, combo_box_samePageSize, "samePageSize", args, "samePageSize",
                        fun_to_apply=str_to_bool)

    update_funs.append(update_samePageSize)

    ##
    ## Code for pages option.
    ##

    args_dict["pages"] = args.pages if args.pages else ""
    text_pages = sg.Text("pages", pad=((0,25), None),
                      tooltip=get_help_text_string_for_tooltip(cmd_parser, "pages"))
    input_text_pages = sg.InputText(args_dict["pages"],
                                 size=(7, 1), do_not_clear=True, key="pages")

    def update_pages_values(values_dict):
        """Update the pages value."""
        value = values_dict["pages"]
        try:
            if value:
                parse_page_range_specifiers(value, set(range(page_count)))
        except ValueError:
            sg.PopupError("Bad page specifier.")
            input_text_pages.Update("")
            args_dict["pages"] = ""
        else:
            args_dict["pages"] = values_dict["pages"]
        # Copy backing value to the actual args object.
        args.pages = args_dict["pages"] if args_dict["pages"] else None

    update_funs.append(update_pages_values)

    ##
    ## Code for evenodd option.
    ##

    text_evenodd = sg.Text("evenodd",
                      tooltip=get_help_text_string_for_tooltip(cmd_parser, "evenodd"))

    # BUG: default values not set unless they are strings!
    combo_box_evenodd = sg.Combo(["True", "False"], readonly=True, default_value=str(args.evenodd),
                                       size=(5, 1), key="evenodd", enable_events=True)

    def update_evenodd(values_dict):
        """Update the evenodd values."""
        update_combo_box(values_dict, combo_box_evenodd, "evenodd", args, "evenodd",
                        fun_to_apply=str_to_bool)

    update_funs.append(update_evenodd)

    ##
    ## Code for setPageRatios option.
    ##

    args_dict["setPageRatios"] = args.setPageRatios if args.setPageRatios else ""
    text_setPageRatios = sg.Text("setPageRatios", pad=((0,25), None),
                      tooltip=get_help_text_string_for_tooltip(cmd_parser, "setPageRatios"))
    input_text_setPageRatios = sg.InputText(args_dict["setPageRatios"],
                                 size=(7, 1), do_not_clear=True, key="setPageRatios")

    def update_setPageRatios_values(values_dict):
        """Update the setPageRatios value."""
        value = values_dict["setPageRatios"]
        try:
            if value:
                parse_page_ratio_argument(value)
        except ValueError:
            sg.PopupError("Bad page ratio specifier.")
            input_text_setPageRatios.Update("")
            args_dict["setPageRatios"] = ""
        else:
            args_dict["setPageRatios"] = values_dict["setPageRatios"]
        # Copy backing value to the actual args object.
        if args_dict["setPageRatios"]:
            args.setPageRatios = parse_page_ratio_argument(args_dict["setPageRatios"])
        else:
            args.setPageRatios = None

    update_funs.append(update_setPageRatios_values)

    ##
    ## Code for restore.
    ##

    text_restore = sg.Text("restore",
                      tooltip=get_help_text_string_for_tooltip(cmd_parser, "restore"))

    combo_box_restore = sg.Combo(["True", "False"], readonly=True,
                                         default_value=str(args.restore), size=(5, 1),
                                         key="restore", enable_events=True)

    def update_restore(values_dict):
        """Update the restore values."""
        update_combo_box(values_dict, combo_box_restore, "restore", args, "restore",
                        fun_to_apply=str_to_bool)

    update_funs.append(update_restore)

    ##
    ## Code for pageRatioWeights options.
    ##

    args_dict["pageRatioWeights"] = args.pageRatioWeights
    text_pageRatioWeights = sg.Text("pageRatioWeights",
                      tooltip=get_help_text_string_for_tooltip(cmd_parser, "pageRatioWeights"))
    input_text_pageRatioWeights = [sg.InputText(args_dict["pageRatioWeights"][i], size=(5, 1),
                                 do_not_clear=True, key="pageRatioWeights_{}".format(i))
                                 for i in [0,1,2,3]]

    def update_pageRatioWeights_values(values_dict):
        """Update both the pageRatioWeights value and the pageRatioWeights values."""
        update_4_values(input_text_pageRatioWeights, "pageRatioWeights", args_dict, values_dict)

        # Copy backing values to the actual args object.
        args.pageRatioWeights = args_dict["pageRatioWeights"]

    update_funs.append(update_pageRatioWeights_values)

    ##
    ## Code for absolutePreCrop options.
    ##

    args_dict["absolutePreCrop"] = args.absolutePreCrop
    if len(set(args.absolutePreCrop4)) != 1: # Set initial value if all the same.
        args_dict["absolutePreCrop"] = ["N/A"]
    text_absolutePreCrop = sg.Text("absolutePreCrop",
                      tooltip=get_help_text_string_for_tooltip(cmd_parser, "absolutePreCrop"))
    input_text_absolutePreCrop = sg.InputText(args_dict["absolutePreCrop"][0],
                                 size=(5, 1), do_not_clear=True, key="absolutePreCrop")

    # Code for absolutePreCrop4.
    args_dict["absolutePreCrop4"] = args.absolutePreCrop4
    text_absolutePreCrop4 = sg.Text("absolutePreCrop4",
                      tooltip=get_help_text_string_for_tooltip(cmd_parser, "absolutePreCrop4"))
    input_text_absolutePreCrop4 = [sg.InputText(args_dict["absolutePreCrop4"][i], size=(5, 1),
                                 do_not_clear=True, key="absolutePreCrop4_{}".format(i))
                                 for i in [0,1,2,3]]

    def update_absolutePreCrop_values(values_dict):
        """Update both the absolutePreCrop value and the absolutePreCrop4 values."""
        update_paired_1_and_4_values(input_text_absolutePreCrop,
                    input_text_absolutePreCrop4, "absolutePreCrop", "absolutePreCrop4", args_dict, values_dict)
        # Copy backing values to the actual args object.
        args.absolutePreCrop = args_dict["absolutePreCrop"]
        args.absolutePreCrop4 = args_dict["absolutePreCrop4"]

    update_funs.append(update_absolutePreCrop_values)

    ##
    ## Code for threshold option.
    ##

    args_dict["threshold"] = int(args.threshold)
    text_threshold = sg.Text("threshold", pad=((0,5), None),
                      tooltip=get_help_text_string_for_tooltip(cmd_parser, "threshold"))
    input_num_threshold = sg.InputText(args_dict["threshold"],
                                 size=(3, 1), do_not_clear=True, key="threshold")

    def update_threshold_values(values_dict):
        """Update the threshold value."""
        try:
            value = int(values_dict["threshold"])
            args_dict["threshold"] = value
        except ValueError:
            value = args_dict["threshold"]
        input_num_threshold.Update(value)
        # Copy backing value to the actual args object.
        args.threshold = args_dict["threshold"]

    update_funs.append(update_threshold_values)

    ##
    ## Code for numBlurs option.
    ##

    args_dict["numBlurs"] = int(args.numBlurs)
    text_numBlurs = sg.Text("numBlurs", pad=((0,5), None),
                      tooltip=get_help_text_string_for_tooltip(cmd_parser, "numBlurs"))
    input_num_numBlurs = sg.InputText(args_dict["numBlurs"],
                                 size=(2, 1), do_not_clear=True, key="numBlurs")

    def update_numBlurs_values(values_dict):
        """Update the numBlurs value."""
        try:
            value = int(values_dict["numBlurs"])
            args_dict["numBlurs"] = value
        except ValueError:
            value = args_dict["numBlurs"]
        input_num_numBlurs.Update(value)
        # Copy backing value to the actual args object.
        args.numBlurs = args_dict["numBlurs"]

    update_funs.append(update_numBlurs_values)

    ##
    ## Code for numSmooths option.
    ##

    args_dict["numSmooths"] = int(args.numSmooths)
    text_numSmooths = sg.Text("numSmooths", pad=((0,5), None),
                      tooltip=get_help_text_string_for_tooltip(cmd_parser, "numSmooths"))
    input_num_numSmooths = sg.InputText(args_dict["numSmooths"],
                                 size=(2, 1), do_not_clear=True, key="numSmooths")

    def update_numSmooths_values(values_dict):
        """Update the numSmooths value."""
        try:
            value = int(values_dict["numSmooths"])
            args_dict["numSmooths"] = value
        except ValueError:
            value = args_dict["numSmooths"]
        input_num_numSmooths.Update(value)
        # Copy backing value to the actual args object.
        args.numSmooths = args_dict["numSmooths"]

    update_funs.append(update_numSmooths_values)


    ##
    ## Code for wait indicator text box.
    ##

    wait_indicator_text = sg.Text("Calculating the crop,\nthis may take a while...",
                                  size=(None, None),
                                  auto_size_text=None,
                                  relief=sg.RELIEF_GROOVE,
                                  font=('Lucidia', 11),
                                  text_color=None,
                                  background_color="#DDDDDD",
                                  justification="center",
                                  visible=False)

    ##
    ## Setup and assign the window's layout.
    ##

    layout = [ # The window layout.
        [
            sg.Button("Prev"),
            sg.Button("Next"),
            text_page_num,
            input_text_page_num,
            sg.Text("({})      ".format(page_count)), # Show max page count.
            sg.Button("Toggle Zoom"),
            sg.Text("(arrow keys navigate while zooming)"),
            ],
        [
            image_element,
            sg.Column([
                    [sg.Text("Quadruples are left, bottom, right, and top margins.\n"
                             "Hover to show option-description tooltips.",
                             relief=sg.RELIEF_GROOVE, pad=(None, (0,15)))],
                    [combo_box_uniform, text_uniform, combo_box_samePageSize, text_samePageSize],
                    [input_text_percentRetain, text_percentRetain],
                    # Python 2 can't unpack in list, so use comprehension.
                    [i for i in input_text_percentRetain4] + [text_percentRetain4],
                    [input_text_absoluteOffset, text_absoluteOffset],
                    [i for i in input_text_absoluteOffset4] + [text_absoluteOffset4],
                    [input_text_uniformOrderStat, text_uniformOrderStat],
                    [i for i in input_text_uniformOrderStat4] + [text_uniformOrderStat4],
                    [input_text_pages, text_pages, combo_box_evenodd, text_evenodd],
                    [input_text_setPageRatios, text_setPageRatios, combo_box_restore, text_restore],
                    [i for i in input_text_pageRatioWeights] + [text_pageRatioWeights],
                    [input_text_absolutePreCrop, text_absolutePreCrop],
                    [i for i in input_text_absolutePreCrop4] + [text_absolutePreCrop4],
                    [input_num_threshold, text_threshold, input_num_numBlurs,
                        text_numBlurs, input_num_numSmooths, text_numSmooths],
                    [sg.Button("Crop"), sg.Button("Original"), sg.Button("Exit"),],
                    [sg.Text("")], # This is just for vertical space.
                    [sg.Text("", size=(5, 2)), wait_indicator_text],
                ]),
            ],
    ]

    window.Layout(layout)

    # Note from manual: "If you want to call an element's Update method or call
    # a Graph element's drawing primitives, you must either call Read or
    # Finalize prior to making those calls."
    btn, values_dict = window.Read(timeout=0)
    #call_all_update_funs(update_funs, values_dict)

    ##
    ## Define the buttons/events we want to handle.
    ##

    def is_Enter(btn):
        return btn.startswith("Return:") or btn == chr(13)

    def is_Exit(btn):
        return btn == chr(27) or btn.startswith("Escape:") or btn.startswith("Exit")

    def is_Crop(btn):
        return btn.startswith("Crop")

    def is_Original(btn):
        return btn.startswith("Original")

    def is_Next(btn):
        return btn.startswith("Next") or btn == "MouseWheel:Down" # Note mouse not giving any event.

    def is_Prev(btn):
        return btn.startswith("Prior:") or btn.startswith("Prev") or btn == "MouseWheel:Up"

    def is_Up(btn):
        return btn.startswith("Up:")

    def is_Down(btn):
        return btn.startswith("Down:")

    def is_Left(btn):
        return btn.startswith("Left:")

    def is_Right(btn):
        return btn.startswith("Right:")

    def is_Zoom(btn):
        return btn.startswith("Toggle Zoom")

    def is_page_mod_key(btn):
        return any((is_Enter(btn), is_Next(btn), is_Prev(btn), is_Zoom(btn)))

    ##
    ## Run the main event loop.
    ##

    zoom = False
    did_crop = False
    bounding_box_list = None

    last_pre_crop = None
    last_threshold = None
    last_numSmooths = None
    last_numBlurs = None

    while True:
        btn, values_dict = window.Read()

        if btn is None and (values_dict is None or values_dict["PageNumber"] is None):
            break
        if is_Exit(btn):
            break

        if is_Enter(btn):
            call_all_update_funs(update_funs, values_dict)
            try:
                cur_page = int(values_dict["PageNumber"]) - 1  # check if valid
            except:
                cur_page = 0

        elif is_Next(btn):
            cur_page += 1

        elif is_Prev(btn):
            cur_page -= 1

        elif is_Up(btn) and zoom:
            zoom = (clip_pos, 0, -1)

        elif is_Down(btn) and zoom:
            zoom = (clip_pos, 0, 1)

        elif is_Left(btn) and zoom:
            zoom = (clip_pos, -1, 0)

        elif is_Right(btn) and zoom:
            zoom = (clip_pos, 1, 0)

        elif is_Zoom(btn): # Toggle.
            if not zoom:
                zoom = (clip_pos, 0, 0)
            else:
                zoom = False

        elif is_Crop(btn):
            call_all_update_funs(update_funs, values_dict)
            document.close()

            # Display the wait message.
            #nonblock_popup = sg.PopupNoWait(
            #        "Finding the bounding boxes,\nthis may take some time...",
            #        keep_on_top=True,
            #        title="pdfCropMargins version {}.".format(__version__),
            #        button_type=5,
            #        button_color=None,
            #        background_color=None,
            #        text_color=None,
            #        auto_close=True,
            #        auto_close_duration=2,
            #        non_blocking=True,
            #        icon=None,
            #        line_width=None,
            #        font=None,
            #        no_titlebar=True,
            #        grab_anywhere=True,
            #        location=(100,100))
            wait_indicator_text.Update(visible=True)
            window.Finalize()

            # If the pre-crop values changed then bounding boxes must be redone.
            all_pre_crop = args.absolutePreCrop + args.absolutePreCrop4
            if last_pre_crop != all_pre_crop:
                bounding_box_list = None # Kill saved bounding boxes.
                last_pre_crop = all_pre_crop
            # New thresholding params also require recalculation of bounding boxes.
            if last_threshold != args.threshold:
                bounding_box_list = None
                last_threshold = args.threshold
            if last_numBlurs != args.numBlurs:
                bounding_box_list = None
                last_numBlurs = args.numBlurs
            if last_numSmooths != args.numSmooths:
                bounding_box_list = None
                last_numSmooths = args.numSmooths

            # Do the crop, saving the bounding box list.
            bounding_box_list = process_pdf_file(input_doc_fname, fixed_input_doc_fname,
                                                 output_doc_fname, bounding_box_list)
            if args.restore:
                combo_box_restore.Update("False")

            # Change the view to the new cropped file.
            page_display_list_cache = [None] * page_count
            document, page_count = open_document(output_doc_fname)
            did_crop = True
            wait_indicator_text.Update(visible = False)

        elif is_Original(btn):
            call_all_update_funs(update_funs, values_dict)
            document.close()
            page_display_list_cache = [None] * page_count
            document, page_count = open_document(fixed_input_doc_fname)
            did_crop = False

        # Update page number.
        cur_page = update_page_number(cur_page, page_count, is_page_mod_key, btn,
                                      input_text_page_num)

        # Get the current page and display it.
        data, clip_pos = get_page(cur_page, page_display_list_cache, document,
                                  window_size=window_size, zoom=zoom)
        image_element.Update(data=data)

    window.Close()
    return did_crop


