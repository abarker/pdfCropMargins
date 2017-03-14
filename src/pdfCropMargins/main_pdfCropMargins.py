"""

pdfCropMargins -- a program to crop the margins of PDF files
Copyright (C) 2014 Allen Barker (Allen.L.Barker@gmail.com)

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

Project web site: https://abarker.github.io/pdfCropMargins
Source code site: https://github.com/abarker/pdfCropMargins

=====================================================================

This script is not the starting point script.  The starting point for the
pdfCropMargins program is to run the the pdfCropMargins.py script.
Equivalently, import the main() function from that script and run it.  The
source directory and the project root directories have __main__.py files which
do this automatically when Python is invoked on their directories.

Note that this application is not a package, just a bunch of scripts in a
directory but it has an __init__.py file to make it easy for setuptools
to find the startup module.

"""

# Possible useful feature to add: Have -ea and -oa options that do absolute
# crops on even and odd differently.  Similarly, -ea4 and -oa4 for individual
# margins.  Similarly -eap and -oap for even vs. odd absolute pre-crops.

# Some general notes, useful for reading the code.
#
# Margins are conveniently described as left, bottom, right, and top, but boxes
# in PDF files are usually defined by the lower-left point's x and y values
# followed by the upper-right point's x and y values.  This is equivalent
# information (since x and y is implicit in the margin names) but the viewpoint
# is slightly different.
#
# This program (like the Ghostscript program) uses the PDF ordering convention
# (lbrt) for listing margins and defining boxes.  Note that PIL uses some
# different conventions.  The origin in PDFs is the lower left going up but the
# origin in PIL images is the upper left going down.  Also, the bounding box
# routine of PIL returns ltrb instead of lbrt.  Keep in mind that the program
# needs to make these conversions when rendering explicitly to images.

from __future__ import print_function, division, absolute_import
import sys
import os
import shutil
import time

##
## Import the module that calls external programs and gets system info.
##

from . import external_program_calls as ex
python_version = ex.python_version
project_src_directory = ex.project_src_directory

##
## Try to import the system pyPdf.  If that fails or if the '--pypdf_local'
## option was set then revert to the appropriate local version.
##

pypdf_local = False # TODO delete cleanup
# Peek at the command line (before fully parsing it later) to see if we should
# import the local pyPdf.  This works for simple options which are either set
# or not.  Note that importing is now dependent on sys.argv (even though it
# shouldn't make a difference in this application).
if "--pypdf_local" in sys.argv or "-pdl" in sys.argv:
    #pypdf_local = True
    pypdf_local = False # NEVER USE LOCAL

try:
    from PyPDF2 import PdfFileWriter, PdfFileReader # the system's pyPdf
    from PyPDF2.generic import \
        NameObject, createStringObject, RectangleObject, FloatObject
    from PyPDF2.utils import PdfReadError
except ImportError:
    print("\nError in pdfCropMargins: No system pyPdf Python package"
          " was found.\n", file=sys.stderr)
    raise

##
## Import the general function for calculating a list of bounding boxes.
##

from .calculate_bounding_boxes import get_bounding_box_list

##
## Import the prettified argparse module and the text of the manpage documentation.
##

from .prettified_argparse import parse_command_line_arguments
from .manpage_data import cmd_parser

##
## Some general strings used by the program.
##

# The string which is appended to Producer metadata in cropped PDFs.
producer_modifier = " (Cropped by pdfCropMargins.)"


##
## Begin general function definitions.
##


def generate_default_filename(infile_path, is_cropped_file=True):
    """Generate the name of the default output file from the name of the input
    file.  The is_cropped_file boolean is used to indicate that the file has been
    (or will be) cropped, to determine which filename-modification string to
    use.  Function assumes that args has been set globally by argparse."""

    if is_cropped_file: suffix = prefix = args.stringCropped
    else: suffix = prefix = args.stringUncropped

    # Use modified basename as output path; program writes default output to CWD.
    file_name = os.path.basename(infile_path)
    nameBeforeExtension, extension = os.path.splitext(file_name)
    if extension not in {".pdf", ".PDF"}: extension += ".pdf"

    sep = args.stringSeparator
    if args.usePrefix: name = prefix + sep + nameBeforeExtension + extension
    else: name = nameBeforeExtension + sep + suffix + extension

    return name


def intersect_boxes(box1, box2):
    """Takes two pyPdf boxes (such as page.mediaBox) and returns the pyPdf
    box which is their intersection."""
    if not box1 and not box2: return None
    if not box1: return box2
    if not box2: return box1
    intersect = RectangleObject([0, 0, 0, 0]) # Note [llx,lly,urx,ury] == [l,b,r,t]
    intersect.upperRight = (min(box1.upperRight[0], box2.upperRight[0]),
                            min(box1.upperRight[1], box2.upperRight[1]))
    intersect.lowerLeft = (max(box1.lowerLeft[0], box2.lowerLeft[0]),
                           max(box1.lowerLeft[1], box2.lowerLeft[1]))
    return intersect


def mod_box_for_rotation(box, angle, undo=False):
    """The user sees left, bottom, right, and top margins on a page, but inside
    the PDF and in pyPdf the page may be rotated (such as in landscape mode).
    In the case of 90 degree clockwise rotation the left really modifies the
    top, the top really modifies right, and so forth.  In order for the options
    like '--percentRetain4' and '--absoluteOffset4' to work as expected the
    values need to be shifted to match any "hidden" rotations on any page."""

    def rotate_ninety_degrees_clockwise(box, n):
        if n == 0: return box
        box = rotate_ninety_degrees_clockwise(box, n-1)
        return [box[1], box[2], box[3], box[0]]

    # These are for clockwise, swap do and undo to reverse.
    do_map = {0: 0, 90: 1, 180: 2, 270: 3}
    undo_map = {0: 0, 90: 3, 180: 2, 270: 1}

    if not undo:
        return rotate_ninety_degrees_clockwise(box, do_map[angle])
    else:
        return rotate_ninety_degrees_clockwise(box, undo_map[angle])
    return


def get_full_page_box_assigning_media_and_crop(page):
    """This returns whatever PDF box was selected (by the user option
    '--fullPageBox') to represent the full page size.  All cropping is done
    relative to this box.  The default selection option is the MediaBox
    intersected with the CropBox so multiple crops work as expected.  The
    argument page should be a pyPdf page object.  This function also by default
    sets the MediaBox and CropBox to the full-page size and saves the old values
    in the same page namespace, and so it should only be called once for each
    page.  It returns a RectangleObject box."""

    # Find the page rotation angle (degrees).
    # Note rotation is clockwise, and four values are allowed: 0 90 180 270
    try:
        rotation = page["/Rotate"].getObject() # this works, needs try
        #rotation = page.get("/Rotate", 0) # from the PyPDF2 source, default 0
    except KeyError:
        rotation = 0
    while rotation >= 360: rotation -= 360
    while rotation < 0: rotation += 360

    # Save the rotation value in the page's namespace so we can restore it later.
    page.rotationAngle = rotation

    # Un-rotate the page, leaving it with an rotation of 0.
    page.rotateClockwise(-rotation)

    # Save copies of some values in the page's namespace, to possibly restore later.
    page.originalMediaBox = page.mediaBox
    page.originalCropBox = page.cropBox

    first_loop = True
    for box_string in args.fullPageBox:
        if box_string == "m": f_box = page.mediaBox
        if box_string == "c": f_box = page.cropBox
        if box_string == "t": f_box = page.trimBox
        if box_string == "a": f_box = page.artBox
        if box_string == "b": f_box = page.bleedBox

        # Take intersection over all chosen boxes.
        if first_loop:
            full_box = f_box
        else:
            full_box = intersect_boxes(full_box, f_box)

        first_loop = False

    # Do any absolute pre-cropping specified for the page (after modifying any
    # absolutePreCrop arguments to take into account rotations to the page).
    a = mod_box_for_rotation(args.absolutePreCrop, rotation)
    full_box = RectangleObject([float(full_box.lowerLeft[0]) + a[0],
                               float(full_box.lowerLeft[1]) + a[1],
                               float(full_box.upperRight[0]) - a[2],
                               float(full_box.upperRight[1]) - a[3]])

    page.mediaBox = full_box
    page.cropBox = full_box

    return full_box


def get_full_page_box_list_assigning_media_and_crop(input_doc, quiet=False):
    """Get a list of all the full-page box values for each page.  The argument
    input_doc should be a PdfFileReader object.  The boxes on the list are in the
    simple 4-float list format used by this program, not RectangleObject format."""

    full_page_box_list = []
    rotation_list = []

    if args.verbose and not quiet:
        print("\nOriginal full page sizes, in PDF format (lbrt):")

    for page_num in range(input_doc.getNumPages()):

        # Get the current page and find the full-page box.
        curr_page = input_doc.getPage(page_num)
        full_page_box = get_full_page_box_assigning_media_and_crop(curr_page)

        if args.verbose and not quiet:
            # want to display page num numbering from 1, so add one
            print("\t"+str(page_num+1), "  rot =",
                  curr_page.rotationAngle, "\t", full_page_box)

        # Convert the RectangleObject to floats in an ordinary list and append.
        ordinary_box = [float(b) for b in full_page_box]
        full_page_box_list.append(ordinary_box)

        # Append the rotation value to the rotation_list.
        rotation_list.append(curr_page.rotationAngle)

    return full_page_box_list, rotation_list


def calculate_crop_list(full_page_box_list, bounding_box_list, angle_list,
                                                               page_nums_to_crop):
    """Given a list of full-page boxes (media boxes) and a list of tight
    bounding boxes for each page, calculate and return another list giving the
    list of bounding boxes to crop down to."""

    # Definition: the deltas are the four differences, one for each margin,
    # between the original full page box and the final, cropped full-page box.
    # In the usual case where margin sizes decrease these are the same as the
    # four margin-reduction values (in absolute points).   The deltas are
    # usually positive but they can be negative due to either percentRetain>100
    # or a large enough absolute offset (in which case the size of the
    # corresponding margin will increase).  When percentRetain<0 the deltas are
    # always greater than the absolute difference between the full page and a
    # tight bounding box, and so part of the text within the tight bounding box
    # will also be cropped (unless absolute offsets are used to counter that).

    num_pages = len(bounding_box_list)
    page_range = range(num_pages)
    num_pages_to_crop = len(page_nums_to_crop)

    # Handle the '--samePageSize' option.
    # Note that this is always done first, even before evenodd is handled.  It
    # is only applied to the pages in `page_nums_to_crop`.
    if args.samePageSize:
        if args.verbose:
            print("\nSetting each page size to the smallest box bounding all the pages.")
        same_size_bounding_box = [
                           min(full_page_box_list[pg][0] for pg in page_nums_to_crop),
                           min(full_page_box_list[pg][1] for pg in page_nums_to_crop),
                           max(full_page_box_list[pg][2] for pg in page_nums_to_crop),
                           max(full_page_box_list[pg][3] for pg in page_nums_to_crop)]
        new_full_page_box_list = []
        for p_num, box in enumerate(full_page_box_list):
            if p_num not in page_nums_to_crop:
                new_full_page_box_list.append(box)
            else:
                new_full_page_box_list.append(same_size_bounding_box)
        full_page_box_list = new_full_page_box_list

    # Handle the '--evenodd' option if it was selected.
    if args.evenodd:
        even_page_nums_to_crop = {p_num for p_num in page_nums_to_crop if p_num % 2 == 0}
        odd_page_nums_to_crop = {p_num for p_num in page_nums_to_crop if p_num % 2 != 0}

        if args.uniform: uniform_set_with_even_odd = True
        else: uniform_set_with_even_odd = False

        # Recurse on even and odd pages, after resetting some options.
        if args.verbose:
            print("\nRecursively calculating crops for even and odd pages.")
        args.evenodd = False # avoid infinite recursion
        args.uniform = True  # --evenodd implies uniform, just on each separate group
        even_crop_list = calculate_crop_list(full_page_box_list, bounding_box_list,
                                             angle_list, even_page_nums_to_crop)
        odd_crop_list = calculate_crop_list(full_page_box_list, bounding_box_list,
                                            angle_list, odd_page_nums_to_crop)

        # Recombine the even and odd pages
        combine_even_odd = []
        for p_num in page_range:
            if p_num % 2 == 0: combine_even_odd.append(even_crop_list[p_num])
            else: combine_even_odd.append(odd_crop_list[p_num])

        # Handle the case where --uniform was set with --evenodd
        if uniform_set_with_even_odd:
            min_bottom_margin = min([box[1] for box in combine_even_odd])
            max_top_margin = max([box[3] for box in combine_even_odd])
            combine_even_odd = [[box[0], min_bottom_margin, box[2], max_top_margin]
                              for box in combine_even_odd]
        return combine_even_odd

    # Before calculating the crops we modify the percentRetain and
    # absoluteOffset values for all the pages according to any specified
    # rotations for the pages.  This is so, for example, uniform cropping is
    # relative to what the user actually sees.
    rotated_percent_retain = [mod_box_for_rotation(args.percentRetain, angle_list[i])
                                                         for i in range(num_pages)]
    rotated_absolute_offset = [mod_box_for_rotation(args.absoluteOffset, angle_list[i])
                                                         for i in range(num_pages)]

    # Calculate the list of deltas to be used to modify the original page
    # sizes.  Basically, a delta is the absolute diff between the full and
    # tight-bounding boxes, scaled according to the user's percentRetain, with
    # any absolute offset then added (lb) or subtracted (tr) as appropriate.
    #
    # The deltas are all positive unless absoluteOffset changes that or
    # percent>100.  They are added (lb) or subtracted (tr) as appropriate.

    delta_list = []
    for p_num, t_box, f_box in zip(list(range(len(full_page_box_list))),
                                               bounding_box_list, full_page_box_list):
        deltas = [abs(t_box[i] - f_box[i]) for i in range(4)]
        adj_deltas = [deltas[i] * (100.0-rotated_percent_retain[p_num][i]) / 100.0
                     for i in range(4)]
        adj_deltas = [adj_deltas[i] + rotated_absolute_offset[p_num][i] for i in range(4)]
        delta_list.append(adj_deltas)

    # Handle the '--uniform' options if one was selected.
    if args.uniformOrderPercent:
        percent_val = args.uniformOrderPercent[0]
        if percent_val < 0.0: percent_val = 0.0
        if percent_val > 100.0: percent_val = 100.0
        args.uniformOrderStat = [int(round(num_pages_to_crop * percent_val / 100.0))]

    if args.uniform or args.uniformOrderStat:
        if args.verbose:
            print("\nAll the selected pages will be uniformly cropped.")
        # Only look at the deltas which correspond to pages selected for cropping.
        # They will then be sorted for each margin and selected.
        crop_delta_list = [delta_list[j] for j in page_range if j in page_nums_to_crop]

        i = 0 # For order stats, let i be the index value into the sorted delta list.
        if args.uniformOrderStat:
            i = args.uniformOrderStat[0]
        if i < 0 or i >= num_pages_to_crop:
            print("\nWarning: The selected order statistic is out of range.",
                  "Setting to closest value.", file=sys.stderr)
            if i >= num_pages_to_crop:
                i = num_pages_to_crop - 1
            if i < 0:
                i = 0
        if args.verbose and (args.uniformOrderStat or args.uniformOrderPercent):
            print("\nThe " + str(i) +
                  " smallest delta values over the selected pages will be ignored"
                  "\nwhen choosing a common, uniform delta value for each margin.")
        left_vals = sorted([box[0] for box in crop_delta_list])
        lower_vals = sorted([box[1] for box in crop_delta_list])
        right_vals = sorted([box[2] for box in crop_delta_list])
        upper_vals = sorted([box[3] for box in crop_delta_list])
        delta_list = [[left_vals[i], lower_vals[i],
                      right_vals[i], upper_vals[i]]] * num_pages

    # Apply the delta modifications to the full boxes to get the final sizes.
    final_crop_list = []
    for f_box, deltas in zip(full_page_box_list, delta_list):
        final_crop_list.append((f_box[0] + deltas[0], f_box[1] + deltas[1],
                                f_box[2] - deltas[2], f_box[3] - deltas[3]))

    return final_crop_list


def set_cropped_metadata(input_doc, output_doc, InputMetadataInfo):
    """Set the metadata for the output document.  Mostly just copied over, but
    "Producer" has a string appended to indicate that this program modified the
    file.  That allows for the undo operation to make sure that this
    program cropped the file in the first place."""

    # Setting metadata with pyPdf requires low-level pyPdf operations, see
    # http://stackoverflow.com/questions/2574676/change-metadata-of-pdf-file-with-pypdf
    if not InputMetadataInfo: # In case it's null, just set values to empty strings.
        class InputMetadataInfo(object):
            pass
        InputMetadataInfo.author = ""
        InputMetadataInfo.creator = ""
        InputMetadataInfo.producer = ""
        InputMetadataInfo.subject = ""
        InputMetadataInfo.title = ""

    output_info_dict = output_doc._info.getObject()

    # Check Producer metadata attribute to see if this program cropped document before.
    global producer_modifier
    already_cropped_by_this_program = False
    old_producer_string = InputMetadataInfo.producer
    if old_producer_string and old_producer_string.endswith(producer_modifier):
        if args.verbose:
            print("\nThe document was already cropped at least once by this program.")
        already_cropped_by_this_program = True
        producer_modifier = "" # No need to pile up suffixes each time on Producer.

    # Note that all None metadata attributes are currently set to the empty string
    # when passing along the metadata information.
    def st(item):
        if item is None: return ""
        else: return item

    output_info_dict.update({
          NameObject("/Author"): createStringObject(st(InputMetadataInfo.author)),
          NameObject("/Creator"): createStringObject(st(InputMetadataInfo.creator)),
          NameObject("/Producer"): createStringObject(st(InputMetadataInfo.producer)
                                                                 + producer_modifier),
          NameObject("/Subject"): createStringObject(st(InputMetadataInfo.subject)),
          NameObject("/Title"): createStringObject(st(InputMetadataInfo.title))
          })

    return already_cropped_by_this_program


def apply_crop_list(crop_list, input_doc, page_nums_to_crop,
                                                       already_cropped_by_this_program):
    """Apply the crop list to the pages of the input PdfFileReader object."""

    if args.restore and not already_cropped_by_this_program:
        print("\nWarning from pdfCropMargins: The Producer string indicates that"
              "\neither this document was not previously cropped by pdfCropMargins"
              "\nor else it was modified by another program after that.  Trying the"
              "\nundo anyway...", file=sys.stderr)

    if args.restore and args.verbose:
        print("\nRestoring the document to margins saved for each page in the ArtBox.")

    if args.verbose and not args.restore:
        print("\nNew full page sizes after cropping, in PDF format (lbrt):")

    # Copy over each page, after modifying the appropriate PDF boxes.
    for page_num in range(input_doc.getNumPages()):

        curr_page = input_doc.getPage(page_num)

        # Restore any rotation which was originally on the page.
        curr_page.rotateClockwise(curr_page.rotationAngle)

        # Only do the restore from ArtBox if '--restore' option was selected.
        if args.restore:
            if not curr_page.artBox:
                print("\nWarning from pdfCropMargins: Attempting to restore pages from"
                      "\nthe ArtBox in each page, but page", page_num, "has no readable"
                      "\nArtBox.  Leaving that page unchanged.", file=sys.stderr)
                continue
            curr_page.mediaBox = curr_page.artBox
            curr_page.cropBox = curr_page.artBox
            continue

        # Do the save to ArtBox if that option is chosen and Producer is set.
        if not args.noundosave and not already_cropped_by_this_program:
            curr_page.artBox = intersect_boxes(curr_page.mediaBox, curr_page.cropBox)

        # Reset the CropBox and MediaBox to their saved original values
        # (which were set in getFullPageBox, in the curr_page object's namespace).
        curr_page.mediaBox = curr_page.originalMediaBox
        curr_page.cropBox = curr_page.originalCropBox

        # Copy the original page without further mods if it wasn't in the range
        # selected for cropping.
        if page_num not in page_nums_to_crop:
            continue

        # Convert the computed "box to crop to" into a RectangleObject (for pyPdf).
        new_cropped_box = RectangleObject(crop_list[page_num])

        if args.verbose:
            print("\t"+str(page_num+1)+"\t", new_cropped_box) # page numbering from 1

        if not args.boxesToSet:
            args.boxesToSet = ["m", "c"]

        # Now set any boxes which were selected to be set via the --boxesToSet option.
        if "m" in args.boxesToSet: curr_page.mediaBox = new_cropped_box
        if "c" in args.boxesToSet: curr_page.cropBox = new_cropped_box
        if "t" in args.boxesToSet: curr_page.trimBox = new_cropped_box
        if "a" in args.boxesToSet: curr_page.artBox = new_cropped_box
        if "b" in args.boxesToSet: curr_page.bleedBox = new_cropped_box

    return


##############################################################################
#
# Begin the main script.
#
##############################################################################


# Parse the command-line arguments and set the variable args.
args = parse_command_line_arguments(cmd_parser)


def main_crop():
    """This function does the real work.  It is called by main() in
    pdfCropMargins.py, which just handles catching exceptions and cleaning up."""

    ##
    ## Process some of the command-line arguments.
    ##

    if args.verbose:
        print("\nProcessing the PDF with pdfCropMargins...\nSystem type:",
              ex.system_os)

    if args.gsBbox and len(args.fullPageBox) > 1:
        print("\nWarning: only one --fullPageBox value can be used with the -gs option.",
              "\nIgnoring all but the first one.", file=sys.stderr)
        args.fullPageBox = [args.fullPageBox[0]]
    elif args.gsBbox and not args.fullPageBox: args.fullPageBox = ["c"] # gs default
    elif not args.fullPageBox: args.fullPageBox = ["m", "c"] # usual default

    if args.verbose:
        print("\nFor the full page size, using values from the PDF box"
              "\nspecified by the intersection of these boxes:", args.fullPageBox)

    if args.absolutePreCrop: args.absolutePreCrop *= 4 # expand to 4 offsets
    # See if all four offsets are explicitly set and use those if so.
    if args.absolutePreCrop4: args.absolutePreCrop = args.absolutePreCrop4
    if args.verbose:
        print("\nThe absolute pre-crops to be applied to each margin, in units of bp,"
              " are:\n   ", args.absolutePreCrop)

    if args.percentRetain: args.percentRetain *= 4 # expand to 4 percents
    # See if all four percents are explicitly set and use those if so.
    if args.percentRetain4: args.percentRetain = args.percentRetain4
    if args.verbose:
        print("\nThe percentages of margins to retain are:\n   ",
              args.percentRetain)

    if args.absoluteOffset: args.absoluteOffset *= 4 # expand to 4 offsets
    # See if all four offsets are explicitly set and use those if so.
    if args.absoluteOffset4: args.absoluteOffset = args.absoluteOffset4
    if args.verbose:
        print("\nThe absolute offsets to be applied to each margin, in units of bp,"
              " are:\n   ", args.absoluteOffset)

    if len(args.pdf_input_doc) > 1:
        print("\nError in pdfCropMargins: Only one input PDF document is allowed."
              "\nFound more than one on the command line:", file=sys.stderr)
        for f in args.pdf_input_doc:
            print("   ", f, file=sys.stderr)
        ex.cleanup_and_exit(1)

    input_doc_fname = ex.glob_if_windows_os(args.pdf_input_doc[0], exact_num_args=1)[0]
    if not input_doc_fname.endswith((".pdf",".PDF")):
        print("\nWarning in pdfCropMargins: The file extension is neither '.pdf'"
              "\nnor '.PDF'; continuing anyway.\n", file=sys.stderr)
    if args.verbose:
        print("\nThe input document's filename is:\n   ", input_doc_fname)
    if not os.path.isfile(input_doc_fname):
        print("\nError in pdfCropMargins: The specified input file\n   "
              + input_doc_fname + "\nis not a file or does not exist.",
              file=sys.stderr)
        ex.cleanup_and_exit(1)

    if not args.outfile:
        if args.verbose: print("\nUsing the default-generated output filename.")
        output_doc_fname = generate_default_filename(input_doc_fname)
    else:
        output_doc_fname = ex.glob_if_windows_os(args.outfile[0], exact_num_args=1)[0]
    if args.verbose:
        print("\nThe output document's filename will be:\n   ", output_doc_fname)

    if os.path.lexists(output_doc_fname) and args.noclobber:
        print("\nOption '--noclobber' is set, refusing to overwrite an existing"
              "\nfile with filename:\n   ", output_doc_fname, file=sys.stderr)
        ex.cleanup_and_exit(1)

    if os.path.lexists(output_doc_fname) and ex.samefile(input_doc_fname,
                                                                output_doc_fname):
        print("\nError in pdfCropMargins: The input file is the same as"
              "\nthe output file.\n", file=sys.stderr)
        ex.cleanup_and_exit(1)

    if args.pdftoppmPath: ex.set_pdftoppm_executable_to_string(args.pdftoppmPath)
    if args.ghostscriptPath: ex.set_gs_executable_to_string(args.ghostscriptPath)

    # If the option settings require pdftoppm, make sure we have a running
    # version.  If '--gsBbox' isn't chosen then assume that PDF pages are to be
    # explicitly rendered.  In that case we either need pdftoppm or gs to do the
    # rendering.
    gs_render_fallback_set = False # Set True if we switch to gs option as a fallback.
    if not args.gsBbox and not args.gsRender:
        found_pdftoppm = ex.init_and_test_pdftoppm_executable(
                                                   prefer_local=args.pdftoppmLocal)
        if args.verbose: print("\nFound pdftoppm program at:", found_pdftoppm)
        if not found_pdftoppm:
            args.gsRender = True
            gs_render_fallback_set = True
            if args.verbose:
                print("\nNo pdftoppm executable found; using Ghostscript for rendering.")

    # If any options require Ghostscript, make sure it it installed.
    if args.gsBbox or args.gsFix or args.gsRender:
        found_gs = ex.init_and_test_gs_executable()
        if args.verbose: print("\nFound Ghostscript program at:", found_gs)
    if args.gsBbox and not found_gs:
        print("\nError in pdfCropMargins: The '--gsBbox' option was specified but"
              "\nthe Ghostscript executable could not be located.  Is it"
              "\ninstalled and in the PATH for command execution?\n", file=sys.stderr)
        ex.cleanup_and_exit(1)
    if args.gsFix and not found_gs:
        print("\nError in pdfCropMargins: The '--gsFix' option was specified but"
              "\nthe Ghostscript executable could not be located.  Is it"
              "\ninstalled and in the PATH for command execution?\n", file=sys.stderr)
        ex.cleanup_and_exit(1)
    if args.gsRender and not found_gs:
        if gs_render_fallback_set:
            print("\nError in pdfCropMargins: Neither Ghostscript nor pdftoppm"
                  "\nwas found in the PATH for command execution.  At least one is"
                  "\nrequired.\n", file=sys.stderr)
        else:
            print("\nError in pdfCropMargins: The '--gsRender' option was specified but"
                  "\nthe Ghostscript executable could not be located.  Is it"
                  "\ninstalled and in the PATH for command execution?\n", file=sys.stderr)
        ex.cleanup_and_exit(1)

    # Give a warning message if incompatible option combinations have been selected.
    if args.gsBbox and args.threshold:
        print("\nWarning in pdfCropMargins: The '--threshold' option is ignored"
              "\nwhen the '--gsBbox' option is also selected.\n", file=sys.stderr)
    if args.gsBbox and args.numBlurs:
        print("\nWarning in pdfCropMargins: The '--numBlurs' option is ignored"
              "\nwhen the '--gsBbox' option is also selected.\n", file=sys.stderr)
    if args.gsBbox and args.numSmooths:
        print("\nWarning in pdfCropMargins: The '--numSmooths' option is ignored"
              "\nwhen the '--gsBbox' option is also selected.\n", file=sys.stderr)

    ##
    ## Open the input document in a PdfFileReader object.  Due to an apparent bug
    ## in pyPdf we open two PdfFileReader objects for the file.  The time required should
    ## still be small relative to finding the bounding boxes of pages.  The bug is
    ## that writing a PdfFileWriter tends to hang on certain files if 1) pages from
    ## the same PdfFileReader are shared between two PdfFileWriter objects, or 2)
    ## the PdfFileWriter is written, the pages are modified, and there is an attempt
    ## to write the same PdfFileWriter to a different file.
    ##

    if args.gsFix:
        if args.verbose:
            print("\nAttempting to fix the PDF input file before reading it...")
        fixed_input_doc_fname = ex.fix_pdf_with_ghostscript_to_tmp_file(input_doc_fname)
    else:
        fixed_input_doc_fname = input_doc_fname

    fixed_input_doc_file_object = open(fixed_input_doc_fname, "rb")
    try:
        input_doc = PdfFileReader(fixed_input_doc_file_object)
        tmp_input_doc = PdfFileReader(fixed_input_doc_file_object)
    #except PdfReadError, ValueError: # throws various errors, just use general except
    except:
        print("\nError in pdfCropMargins: The pyPdf module failed in an attempt"
              "\nto read the input file.  Is the file a PDF file?  If so then it"
              "\nmay be corrupted.  If you have Ghostscript, try the '--gsFix'"
              "\noption (assuming you are not using it already).  That option can"
              "\nalso convert some PostScript files to a readable format.",
              file=sys.stderr)
        ex.cleanup_and_exit(1)

    ##
    ## See if the document needs to be decrypted.
    ##

    if args.password:
        try:
            input_doc.decrypt(args.password)
            tmp_input_doc.decrypt(args.password)
        except KeyError:
            print("\nDecrypting with the password from the '--password' option"
                  "\nfailed.", file=sys.stderr)
            ex.cleanup_and_exit(1)
    else: # try decrypting with an empty password
        try:
            input_doc.decrypt("")
            tmp_input_doc.decrypt("")
        except KeyError:
            pass # document apparently wasn't encrypted with an empty password

    ##
    ## Print out some data and metadata in verbose mode.
    ##

    if args.verbose:
        print("\nThe input document has %s pages." % input_doc.getNumPages())

    try: # This is needed because the call sometimes just raises an error.
        metadata_info = input_doc.getDocumentInfo()
    except:
        metadata_info = None

    if args.verbose and not metadata_info:
        print("\nNo readable metadata in the document.")
    elif args.verbose:
        print("\nThe document's metadata, if set:\n")
        print("   The Author attribute set in the input document is:\n      %s"
              % (metadata_info.author))
        print("   The Creator attribute set in the input document is:\n      %s"
              % (metadata_info.creator))
        print("   The Producer attribute set in the input document is:\n      %s"
              % (metadata_info.producer))
        print("   The Subject attribute set in the input document is:\n      %s"
              % (metadata_info.subject))
        print("   The Title attribute set in the input document is:\n      %s"
              % (metadata_info.title))

    ##
    ## Now compute the set containing the pyPdf page number of all the pages
    ## which the user has selected for cropping from the command line.  Most
    ## calculations are still carried-out for all the pages in the document.
    ## (There are a few optimizations for expensive operations like finding
    ## bounding boxes; the rest is negligible).  This keeps the correspondence
    ## between page numbers and the positions of boxes in the box lists.  The
    ## function apply_crop_list then just ignores the cropping information for any
    ## pages which were not selected.
    ##

    all_page_nums = set(range(0, input_doc.getNumPages()))
    page_nums_to_crop = set() # Note that this set holds page num MINUS ONE, start at 0.
    if args.pages:
        # Parse any page range specifier argument.
        for page_num_or_range in args.pages.split(","):
            split_range = page_num_or_range.split("-")
            try:
                if len(split_range) == 1:
                    # Note pyPdf page nums start at 0, not 1 like usual PDF pages,
                    # subtract 1.
                    page_nums_to_crop.add(int(split_range[0])-1)
                else:
                    page_nums_to_crop.update(
                        set(range(int(split_range[0])-1, int(split_range[1]))))
            except ValueError:
                print(
                    "\nError in pdfCropMargins: The page range specified on the command",
                    "\nline contains a non-integer value or otherwise cannot be parsed.",
                    file=sys.stderr)
                ex.cleanup_and_exit(1)
        page_nums_to_crop = page_nums_to_crop & all_page_nums # intersect chosen with actual
    else:
        page_nums_to_crop = all_page_nums

    # Print out the pages to crop in verbose mode.
    if args.verbose and args.pages:
        print("These pages of the document will be cropped:", end="")
        p_num_list = sorted(list(page_nums_to_crop))
        for i in range(len(p_num_list)):
            if i % 10 == 0 and i != len(p_num_list)-1: print("\n   ", end="")
            print("%5d" % (p_num_list[i]+1), " ", end="")
        print("\n")
    elif args.verbose:
        print("\nAll the pages of the document will be cropped.")

    ##
    ## Get a list with the full-page boxes for each page: (left,bottom,right,top)
    ## This function also sets the MediaBox and CropBox of the pages to the
    ## chosen full-page size as a side-effect, saving the old boxes.
    ##

    full_page_box_list, rotation_list = get_full_page_box_list_assigning_media_and_crop(input_doc)
    tmp_full_page_box_list, tmp_rotation_list = get_full_page_box_list_assigning_media_and_crop(
                                                            tmp_input_doc, quiet=True)

    ##
    ## Define the PdfFileWriter object and insert all the input_doc pages into it.
    ## Note that inserting pages from a PdfFileReader into multiple PdfFileWriters
    ## seems to cause problems (writer can hang on write), so only one is used.
    ##

    output_doc = PdfFileWriter()
    for page in [input_doc.getPage(i) for i in range(input_doc.getNumPages())]:
        output_doc.addPage(page)

    tmp_output_doc = PdfFileWriter()
    for page in [tmp_input_doc.getPage(i) for i in range(tmp_input_doc.getNumPages())]:
        tmp_output_doc.addPage(page)

    ##
    ## Write out the PDF document again, with the CropBox and MediaBox reset.
    ## This temp version is only used for calculating the bounding boxes of
    ## pages.  Note we are writing from tmpOutputDocument (due to an apparent bug
    ## discussed above).  After this tmp_input_doc and tmp_output_doc are no longer
    ## needed.
    ##

    if not args.restore:
        doc_with_crop_and_media_boxes_name = ex.get_temporary_filename(".pdf")
        doc_with_crop_and_media_boxes_object = open(
                                     doc_with_crop_and_media_boxes_name, "wb")

        if args.verbose:
            print("\nWriting out the PDF with the CropBox and MediaBox redefined.")

        try:
            tmp_output_doc.write(doc_with_crop_and_media_boxes_object)
        except KeyError:
            print("\nError in pdfCropMargins: The pyPdf program failed in trying to"
                  "\nwrite out a PDF file of the document.  The document may be"
                  "\ncorrupted.  If you have Ghostscript, try using the '--gsFix'"
                  "\noption (assuming you are not already using it).", file=sys.stderr)
            ex.cleanup_and_exit(1)

        doc_with_crop_and_media_boxes_object.close()

    ##
    ## Copy the metadata from inputDot to output_doc, modifying the Producer string
    ## if this program didn't already set it.  Get bool for whether this program
    ## cropped the document already.
    ##

    already_cropped_by_this_program = set_cropped_metadata(input_doc, output_doc,
                                                     metadata_info)

    ##
    ## Calculate the bounding_box_list containing tight page bounds for each page.
    ##

    if not args.restore:
        bounding_box_list = get_bounding_box_list(doc_with_crop_and_media_boxes_name,
                input_doc, full_page_box_list, page_nums_to_crop, args, PdfFileWriter)
        if args.verbose:
            print("\nThe bounding boxes are:")
            for pNum, b in enumerate(bounding_box_list):
                print("\t", pNum+1, "\t", b)

    ##
    ## Calculate the crop_list based on the fullpage boxes and the bounding boxes.
    ##

    if not args.restore:
        crop_list = calculate_crop_list(full_page_box_list, bounding_box_list,
                                     rotation_list, page_nums_to_crop)
    else:
        crop_list = None # Restore, not needed in this case.

    ##
    ## Apply the calculated crops to the pages of the PdfFileReader input_doc.
    ## This also modifies the same pages in the PdfFileWriter output_doc.
    ##

    apply_crop_list(crop_list, input_doc, page_nums_to_crop,
                                          already_cropped_by_this_program)

    ##
    ## Write the final PDF out to a file.
    ##

    if args.verbose: print("\nWriting the cropped PDF file.")

    output_doc_stream = open(output_doc_fname, "wb")
    try:
        output_doc.write(output_doc_stream)
    except KeyError:
        print("\nError in pdfCropMargins: The pyPdf program failed in trying to"
              "\nwrite out a PDF file of the document.  The document may be"
              "\ncorrupted.  If you have Ghostscript, try using the '--gsFix'"
              "\noption (assuming you are not already using it).", file=sys.stderr)
        ex.cleanup_and_exit(1)
    # Experimental test in line below to catch if it hangs... still causes bugs...
    #completed = ex.function_call_with_timeout(output_doc.write, [output_doc_stream], secs=0)
    output_doc_stream.close()
    completed = True
    if not completed:
        print("Sorry, the PDF writer is taking longer than the timeout time.  Exiting.",
              file=sys.stderr)
        ex.cleanup_and_exit(1)

    # We're finished with this open file; close it; let temp dir removal delete it.
    fixed_input_doc_file_object.close()

    ##
    ## Now handle the options which apply after the file is written.
    ##

    def do_preview(output_doc_fname):
        viewer = args.preview
        if args.verbose:
            print("\nPreviewing the output document with viewer:\n   ", viewer)
        ex.show_preview(viewer, output_doc_fname)
        return

    # Handle the '--queryModifyOriginal' option.
    if args.queryModifyOriginal:
        if args.preview:
            print("\nRunning the preview viewer on the file, will query whether or not"
                  "\nto modify the original file after the viewer is launched in the"
                  "\nbackground...\n")
            do_preview(output_doc_fname)
            # Give preview time to start; it may write startup garbage to the terminal...
            query_wait_time = 1 # seconds
            time.sleep(query_wait_time)
            print()
        while True:
            query_string = "\nModify the original file to the cropped file " \
                "(saving the original)? [yn] "
            if ex.python_version[0] == "2":
                query_result = raw_input(query_string).decode("utf-8")
            else:
                query_result = input(query_string)
            if query_result in ["y", "Y"]:
                args.modifyOriginal = True
                print("\nModifying the original file.")
                break
            elif query_result in ["n", "N"]:
                print("\nNot modifying the original file.  The cropped file is saved"
                      " as:\n   {0}".format(output_doc_fname))
                args.modifyOriginal = False
                break
            else:
                print("Response must be in the set {y,Y,n,N}, none recognized.")
                continue

    # Handle the '--modifyOriginal' option.
    if args.modifyOriginal:
        generated_uncropped_filename = generate_default_filename(
                                                  input_doc_fname, is_cropped_file=False)

        # Remove any existing file with the name generated_uncropped_filename unless a
        # relevant noclobber option is set or it isn't a file.
        if os.path.exists(generated_uncropped_filename):
            if os.path.isfile(generated_uncropped_filename) \
                    and not args.noclobberOriginal and not args.noclobber:
                if args.verbose:
                    print("\nRemoving the file\n   ", generated_uncropped_filename)
                # TODO may want try-except on this; permissions
                os.remove(generated_uncropped_filename)
            else:
                print(
                    "\nA noclobber option is set or not a file; refusing to"
                    " overwrite:\n   ", generated_uncropped_filename,
                    "\nFiles are as if option '--modifyOriginal' were not set.",
                    file=sys.stderr)

        # Move (noclobber) the original file to the name for uncropped files.
        if not os.path.exists(generated_uncropped_filename):
            if args.verbose: print("\nDoing a file move:\n   ", input_doc_fname,
                                   "\nis moving to:\n   ", generated_uncropped_filename)
            shutil.move(input_doc_fname, generated_uncropped_filename)

        # Move (noclobber) the cropped file to the original file's name.
        if not os.path.exists(input_doc_fname):
            if args.verbose: print("\nDoing a file move:\n   ", output_doc_fname,
                                   "\nis moving to:\n   ", input_doc_fname)
            shutil.move(output_doc_fname, input_doc_fname)

    # Handle any previewing which still needs to be done.
    if args.preview and not args.queryModifyOriginal: # already previewed in query mod
        if args.modifyOriginal: # already swapped to original filename in this case
            do_preview(input_doc_fname)
        else: # the usual case, preview the output filename
            do_preview(output_doc_fname)

    if args.verbose: print("\nFinished this run of pdfCropMargins.\n")

    return

