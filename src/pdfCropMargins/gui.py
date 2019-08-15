"""

Code to create and execute the GUI when that option is selected.

This code is modified from example/demo code found here:
https://github.com/PySimpleGUI/PySimpleGUI/blob/master/DemoPrograms/Demo_PDF_Viewer.py
Below is the original module docstring:

    @created: 2018-08-19 18:00:00
    @author: (c) 2018-2019 Jorj X. McKie
    Display a PyMuPDF Document using Tkinter
    -------------------------------------------------------------------------------
    Dependencies:
    -------------
    PyMuPDF v1.14.5+, PySimpleGUI, Tkinter

    License:
    --------
    GNU GPL V3+

    Description
    ------------
    Get filename and start displaying page 1. Please note that all file types
    of MuPDF are supported (including EPUB e-books and HTML files for example).
    Pages can be directly jumped to, or buttons can be used for paging.

    This version contains enhancements:
    * PIL no longer needed
    * Zooming is now flexible: only one button serves as a toggle. Keyboard arrow keys can
      be used for moving through the window when zooming.

    We also interpret keyboard events (PageDown / PageUp) and mouse wheel actions
    to support paging as if a button was clicked. Similarly, we do not include
    a 'Quit' button. Instead, the ESCAPE key can be used, or cancelling the form.
    To improve paging performance, we are not directly creating pixmaps from
    pages, but instead from the fitz.DisplayList of the page. Each display list
    will be stored in a list and looked up by page number. This way, zooming
    pixmaps and page re-visits will re-use a once-created display list.

"""
import sys
import os
import fitz

print(fitz.__doc__)

if not list(map(int, fitz.VersionBind.split("."))) >= [1, 14, 5]:
    raise SystemExit("This script requires at least PyMuPDF v1.14.5.")

py2 = str is bytes  # Is this Python 2?
if not py2:
    import PySimpleGUI as sg
    import tkinter as tk
else:
    import PySimpleGUI27 as sg
    import Tkinter as tk

#
# Helper functions.
#

def get_filename():
    """Get the filename of the PDF file if one was not passed in."""
    if len(sys.argv) == 1:
        fname = sg.PopupGetFile("Select file and filetype to open:",
                                title="PyMuPDF Document Browser",
                                file_types=[ # Only PDF files.
                                              ("PDF Files", "*.pdf"),
                                           ],
                                )
    else:
        fname = sys.argv[1]

    if not fname:
        sg.Popup("Cancelling:", "No filename supplied")
        raise SystemExit("Cancelled: no filename supplied")

    return fname

def get_page(page_num, page_display_list_cache, document, zoom=False, max_size=None):
    """Return a `tkinter.PhotoImage` or a PNG image for a document page number.
    - The `page_num` argument is a 0-based page number.
    - The `zoom` argument is the top-left of old clip rect, and one of -1, 0,
      +1 for dim. x or y to indicate the arrow key pressed.
    - The `max_size` argument is the (width, height) of available image area.
      """
    page_display_list = page_display_list_cache[page_num]
    if not page_display_list:  # create if not yet there
        page_display_list_cache[page_num] = document[page_num].getDisplayList()
        page_display_list = page_display_list_cache[page_num]

    rect = page_display_list.rect  # The page rectangle.
    clip = rect
    # Ensure image fits screen: exploit, but do not exceed width or height.
    zoom_0 = 1
    if max_size:
        zoom_0 = min(1, max_size[0] / rect.width, max_size[1] / rect.height)
        if zoom_0 == 1:
            zoom_0 = min(max_size[0] / rect.width, max_size[1] / rect.height)
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

    image_ppm = pixmap.getImageData("ppm")  # make PPM image from pixmap for tkinter
    return image_ppm, clip.tl  # return image, clip position

def get_max_size():
    """Get physical screen dimension to determine the page image max size."""
    root = tk.Tk()
    max_width = root.winfo_screenwidth() - 20
    max_height = root.winfo_screenheight() - 135
    max_size = (max_width, max_height)
    root.destroy()
    del root
    return max_size

#
# Helper functions for updating the values of elements.
#

def update_input_text(input_text_element, value=None, fun_to_apply=None):
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

def call_all_update_funs(update_funs):
    """Call all the functions."""
    for f in update_funs:
        f()

def float_or_NA(value):
    """Convert to float unless the value is 'N/A', which is left unchanged."""
    if value == "N/A":
        return "N/A"
    else:
        return float(value)

def update_paired_1_and_4_values(element, element_list4, attr, attr4, args):
    """Update all the value for pairs such as `percentRetain` and
    `percentRetain4`, keeping the versions with one vs. four arguments
    synchronized."""
    args_attr = getattr(args, attr)
    args_attr4 = getattr(args, attr4)

    element_text = element.Get()
    element_text4 = [element_list4[i].Get() for i in [0,1,2,3]]

    # See if the element value changed.
    if float_or_NA(element_text) != args_attr[0]:
        args_attr[0] = update_input_text(element, fun_to_apply=float_or_NA)
        for i in [0,1,2,3]:
            args_attr4[i] = update_input_text(element_list4[i], value=args_attr[0])

    # See if any of the element_list4 values changed.
    elif any(float(element_text4[i]) != args_attr4[i] for i in [0,1,2,3]):
        for i in [0,1,2,3]:
            args_attr4[i] = update_input_text(element_list4[i], fun_to_apply=float)
        if len(set(args_attr4)) == 1: # All are the same value.
            args_attr[0] = update_input_text(element, value=args_attr4[0])
        else:
            args_attr[0] = update_input_text(element, value="N/A")

    # Just do update to convert forms like 5 to 5.0 (which were equal above).
    update_input_text(element, value=args_attr[0])
    for i in [0,1,2,3]:
        update_input_text(element_list4[i], value=args_attr4[i])

#
# The main function with the event loop.
#

def create_gui(input_doc_fname, parsed_args):
    """Create a GUI for running pdfCropMargins with parsed arguments `parsed_args`
    on the PDF file named `pdf_filename`"""
    args = parsed_args
    document = fitz.open(input_doc_fname)
    page_count = len(document)

    # Allocate storage for caching page display lists.
    page_display_list_cache = [None] * page_count

    title = "pdfCropMargins: {}".format(os.path.basename(input_doc_fname))
    max_size = get_max_size()

    window = sg.Window(title, return_keyboard_events=True, location=(0, 0),
                       use_default_focus=False)
    sg.SetOptions(tooltip_time=500)

    cur_page = 0
    data, clip_pos = get_page(cur_page,  # read first page
                              page_display_list_cache,
                              document,
                              zoom=False,  # not zooming yet
                              max_size=max_size,  # image max dim
                              )

    image_element = sg.Image(data=data)  # make image element

    ## ===================================================

    ## Standin for parsed_args for testing.
    #class args:
    #    """Dummy class mocking argparse args."""
    #    percentRetain = [10.0]
    #    percentRetain4 = [0.0, 1.0, 2.0, 3.0]
    #    absoluteOffset = [10]
    #    absoluteOffset4 = [0.0, 1.0, 2.0, 3.0]

    #if len(set(args.percentRetain4)) != 1: # All the same.
    #    args.percentRetain[0] = "N/A"
    #if len(set(args.absoluteOffset4)) != 1: # All the same.
    #    args.absoluteOffset[0] = "N/A"

    ## ===================================================

    update_funs = [] # A list of all the updating functions.

    #
    # Code for handling page numbers.
    #

    input_text_page_num = sg.InputText(str(cur_page + 1), size=(5, 1),
                                       do_not_clear=True, key="PageNumber")
    text_page_num = sg.Text("Page:")

    def update_page_number(cur_page, page_count, is_page_mod_key, btn,
                           input_text_element):
        # Sanitize page number.
        while cur_page >= page_count:  # wrap around
            cur_page -= page_count
        while cur_page < 0:  # pages < 0 are valid but look bad
            cur_page += page_count

        # Update page number field.
        if is_page_mod_key(btn):
            input_text_element.Update(str(cur_page + 1))
        return cur_page

    #
    # Code for percentRetain.
    #

    text_percentRetain = sg.Text("percentRetain", tooltip=
                                 "Percentage of margin to retain.")
    input_text_percentRetain = sg.InputText(
        args.percentRetain[0], size=(5, 1), do_not_clear=True, key="percentRetain")

    #
    # Code for percentRetain4.
    #

    text_percentRetain4 = sg.Text("percentRetain4", tooltip=
                                 "Percentage of margin to retain.")

    input_text_percentRetain4 = [sg.InputText(args.percentRetain4[i], size=(5, 1),
                                 do_not_clear=True, key="percentRetain4_{}".format(i))
                                 for i in [0,1,2,3]]

    def update_percentRetainValues():
        """Update both the percentRetain value and the percentRetain4 values."""
        update_paired_1_and_4_values(input_text_percentRetain, input_text_percentRetain4,
                               "percentRetain", "percentRetain4", args)
        return

    update_funs.append(update_percentRetainValues)

    #
    # Code for absoluteOffset.
    #

    text_absoluteOffset = sg.Text("absoluteOffset", tooltip=
                                 "Percentage of margin to retain.")
    input_text_absoluteOffset = sg.InputText(
        args.absoluteOffset[0], size=(5, 1), do_not_clear=True, key="absoluteOffset")

    #
    # Code for absoluteOffset4.
    #

    text_absoluteOffset4 = sg.Text("absoluteOffset4", tooltip=
                                 "Percentage of margin to retain.")

    input_text_absoluteOffset4 = [sg.InputText(args.absoluteOffset4[i], size=(5, 1),
                                 do_not_clear=True, key="absoluteOffset4_{}".format(i))
                                 for i in [0,1,2,3]]

    def update_absoluteOffsetValues():
        """Update both the absoluteOffset value and the absoluteOffset4 values."""
        update_paired_1_and_4_values(input_text_absoluteOffset, input_text_absoluteOffset4,
                               "absoluteOffset", "absoluteOffset4", args)
        return

    update_funs.append(update_absoluteOffsetValues)

    #
    # Setup and assign the window's layout.
    #

    layout = [ # The window layout.
        [
            sg.Button("Prev"),
            sg.Button("Next"),
            text_page_num,
            input_text_page_num,
            sg.Text("({})      ".format(page_count)), # Show max page count.
            sg.Button("Toggle Zoom"),
            sg.Text("(arrow keys navigate while zooming)"),
            sg.Text(" "*40 + "Hover to show option-description tooltips."),
            ],
        [
            image_element,
            sg.Column([
                    [input_text_percentRetain, text_percentRetain],
                    [input_text_absoluteOffset, text_absoluteOffset],
                    [sg.Button("Crop"),]
                ]),
            sg.Column([
                    [*input_text_percentRetain4, text_percentRetain4],
                    [*input_text_absoluteOffset4, text_absoluteOffset4],
                    [sg.Button("Exit"),]
                ]),
            ],
    ]

    window.Layout(layout)

    #
    # Define the buttons/events we want to handle.
    #

    def is_Enter(btn):
        return btn.startswith("Return:") or btn == chr(13)

    def is_Exit(btn):
        return btn == chr(27) or btn.startswith("Escape:") or btn.startswith("Exit")

    def is_Crop(btn):
        return btn.startswith("Crop")

    def is_Next(btn):
        return btn.startswith("Next:") or btn == "MouseWheel:Down" # Note mouse not giving any event.

    def is_Prev(btn):
        return btn.startswith("Prior:") or btn == "MouseWheel:Up"

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

    #
    # Run the main event loop.
    #

    zoom = False

    while True:
        btn, value = window.Read()
        #print(btn)

        if btn is None and (value is None or value["PageNumber"] is None):
            break
        if is_Exit(btn):
            break

        if is_Enter(btn):
            call_all_update_funs(update_funs)
            try:
                cur_page = int(value["PageNumber"]) - 1  # check if valid
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
            call_all_update_funs(update_funs)
            #call_fun_to_recrop_file()
            #call_fun_to_update_view_window()

        # Update page number.
        cur_page = update_page_number(cur_page, page_count, is_page_mod_key, btn,
                                      input_text_page_num)

        # Get the current page and display it.
        data, clip_pos = get_page(cur_page, page_display_list_cache, document,
                                  zoom=zoom, max_size=max_size)
        image_element.Update(data=data)

def display_gui(input_doc_fname, parsed_args):
    if not input_doc_fname:
        input_doc_fname = get_filename()
    create_gui(input_doc_fname, parsed_args=parsed_args)

