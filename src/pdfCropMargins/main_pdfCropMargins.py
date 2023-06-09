"""

This script is not the starting/entry point script.  If installed with pip you
can just run `pdfcropmargins` to run the program.  When pip is not used the
starting point for the pdfCropMargins program is to import function `main` from
the `pdfCropMargins.py` script and run it.  The source directory has a
`__main__.py` file which does this automatically when Python is invoked on the
directory.  There is also standalone script in the `bin` directory which is the
preferred way to run the program when it is not installed via pip.

=====================================================================

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

Source code site: https://github.com/abarker/pdfCropMargins

"""

# Might want an option to delete the XML save data.

# TODO GUI options not error-checked/repaired on arg reprocessing, uniformOrderStat
# Separate out the parts of `process_command_line_arguments` that can be re-run from
# the top of `process_pdf_file` each time it is called.  Also allows implementing
# the `--stringRestored` option, which is commented out in manpage file.

# TODO: Maybe use _restored and restored_ prefix and suffix for restore ops???
# Need a new option --stringRestored.

# TODO: Maybe add option to see the MuPdf warnings, use
# fitz.TOOLS.mupdf_warnings() first to empty warnings and then to get warnings,
# see https://github.com/pymupdf/PyMuPDF/discussions/1501

# TODO: Make --evenodd option equalize the pages after separately calculating
# the crops, just do the max over them.

# TODO: Deleting metadata on restore doesn't seem to remove key like docs say.
#       So restored document still registers as already cropped.
#       See the `check_and_set_crop_metadata` function.
#       https://pymupdf.readthedocs.io/en/latest/recipes-low-level-interfaces.html#how-to-extend-pdf-metadata

# Some general notes, useful for reading the code.
#
# Margins are described as left, bottom, right, and top (lbrt). Boxes
# in pypdf2 and PDF are defined by the lower-left point's x and y values
# followed by the upper-right point's x and y values, which is equivalent
# information (since x and y are implicit in the margin names).
# The origin is at the lower left. The pymupdf program uses the top left
# as origin, which results in ltrb ordering:
#
# From: https://github.com/pymupdf/PyMuPDF/issues/317
#    (Py-)MuPDF always uses a page's top-left point as the origin (0,0) of its
#    coordinate system - for whatever reason, prresumably because it does not
#    only deal with PDF, but also other document types.  PDF uses a page's
#    bottom-left point as (0,0).
#
# This program (like the Ghostscript program and pypdf2) uses the PDF ordering
# convention (lbrt) for listing margins and defining boxes.  Note that Pillow
# uses some different conventions.  The origin in PDFs is the lower left going
# up but the origin in Pillow images is the upper left going down.  So the
# bounding box routine of Pillow returns ltrb instead of lbrt.  Keep in mind
# that the program needs to make these conversions when rendering explicitly to
# images.
#
# This program uses pymupdf, but uses the PDF and pypdf2 convention (mainly
# because it originally used pypdf2).  All values are converted by a wrapper
# around the pymupdf routines, which are in the module pymupdf_routines.

import sys
import os
import shutil
import time
from decimal import Decimal
from warnings import warn

try:
    import readline # Makes prompts go to stdout rather than stderr.
except ImportError: # Not available on Windows.
    pass

from . import __version__ # Get the version number from the __init__.py file.
from .manpage_data import cmd_parser, DEFAULT_THRESHOLD_VALUE
from .prettified_argparse import parse_command_line_arguments
from .pymupdf_routines import (has_mupdf, MuPdfDocument, get_box, set_box, Rect,
        intersect_pdf_boxes, fitz)

from . import external_program_calls as ex
project_src_directory = ex.project_src_directory

from .calculate_bounding_boxes import get_bounding_box_list

##
## Some data used by the program.
##

# The string which is appended to Producer metadata in cropped PDFs.
PRODUCER_MODIFIER = " (Cropped by pdfCropMargins.)" # String for older versions.
PRODUCER_MODIFIER_2 = " (Cropped by pdfCropMargins>=2.0.)" # Added to Producer metadata.
RESTORE_METADATA_KEY = "pdfCropMarginsRestoreData" # Key for XML dict restore data.

# Limit precision to some reasonable amount to prevent problems in some PDF viewers.
DECIMAL_PRECISION_FOR_MARGIN_POINT_VALUES = 8

args = None # Global set during cmd-line processing (since almost all funs use it).

##
## Begin general function definitions.
##

def generate_output_filepath(infile_path, is_cropped_file=True,
                             ignore_output_filename=False):
    """Generate the name of the output file from the name of the input file and
    any relevant options selected.

    The `is_cropped_file` boolean is used to indicate that the file has been
    (or will be) cropped, to determine which filename-modification string to
    use.

    If `ignore_output_filename` is true then only the directory path of any
    passed-in output path is used in the generated paths.

    The function assumes that `args` has been set globally by argparse."""
    outfile_dir = os.getcwd() # The default output directory is the CWD.
    if args.outfile:
        globbed_outpath = ex.glob_pathname(args.outfile[0], exact_num_args=1)[0]
        expanded_globbed_outpath = ex.get_expanded_path(globbed_outpath)
        if os.path.isdir(expanded_globbed_outpath): # Output directory was passed in.
            outfile_dir = expanded_globbed_outpath
        else: # Full output path with filename was passed in.
            outfile_dir = os.path.dirname(expanded_globbed_outpath)
            if not ignore_output_filename: # Combine and return the dir and the filename.
                # Note that globbing and expansion is only done on the directory part.
                return os.path.join(outfile_dir, os.path.basename(args.outfile[0]))

    if is_cropped_file:
        suffix = prefix = args.stringCropped
    else:
        suffix = prefix = args.stringUncropped

    # Use modified basename as output path; program writes default output to CWD.
    file_name = os.path.basename(infile_path)
    name_before_extension, extension = os.path.splitext(file_name)
    if extension not in {".pdf", ".PDF"}:
        extension += ".pdf"

    sep = args.stringSeparator
    if args.usePrefix:
        name = prefix + sep + name_before_extension + extension
    else:
        name = name_before_extension + sep + suffix + extension

    name = os.path.join(outfile_dir, name)
    return name

def parse_page_range_specifiers(spec_string, all_page_nums):
    """Parse a page range specifier argument such as "4-5,7,9".  Passed
    a specifier and the set of all page numbers, it returns the subset."""
    page_nums_to_crop = set() # Note that this set holds page num MINUS ONE, start at 0.
    for page_num_or_range in spec_string.split(","):
        split_range = page_num_or_range.split("-")
        if len(split_range) == 1:
            # Note pyPdf page nums start at 0, not 1 like usual PDF pages,
            # subtract 1.
            page_nums_to_crop.add(int(split_range[0])-1)
        else:
            left_arg = int(split_range[0])-1
            right_arg = int(split_range[1])
            if left_arg >= right_arg:
                print("Error in pdfCropMargins: Left argument of page range '{}' cannot"
                      " be less than the right one.".format(spec_string), file=sys.stderr)
                raise ValueError
            page_nums_to_crop.update(set(range(left_arg, right_arg)))
    page_nums_to_crop = page_nums_to_crop & all_page_nums # intersect chosen with actual
    if not page_nums_to_crop: # Empty set of pages.
        print("Error in pdfCropMargins: Page range selection '{}' results in empty"
                " set.".format(spec_string), file=sys.stderr)
        raise ValueError
    return page_nums_to_crop

def parse_page_ratio_argument(ratio_arg):
    """Parse the argument passed to setPageRatios."""
    ratio = ratio_arg.split(":")
    if len(ratio) > 2:
        print("\nError in pdfCropMargins: Bad format in aspect ratio command line"
              " argument.\nToo many colons.", file=sys.stderr)
        raise ValueError
    try:
        if len(ratio) == 2: # Colon form.
            float_ratio = float(ratio[0])/float(ratio[1])
        else: # Float form.
            float_ratio = float(ratio[0])
    except ValueError:
        print("\nError in pdfCropMargins: Bad format in argument to "
              " setPageRatios.\nCannot convert to a float.", file=sys.stderr)
        raise
    if float_ratio == 0 or float_ratio == float("inf"):
        print("\nError in pdfCropMargins: Bad format in argument to "
              " setPageRatios.\nZero or infinite aspect ratios are not allowed.",
              file=sys.stderr)
        raise ValueError
    return float_ratio

def mod_box_for_rotation(box, angle, undo=False):
    """The user sees left, bottom, right, and top margins on a page, but inside
    the PDF and in pyPdf the page may be rotated (such as in landscape mode).
    In the case of 90 degree clockwise rotation the left really modifies the
    top, the top really modifies right, and so forth.  In order for the options
    like '--percentRetain4' and '--absoluteOffset4' to work as expected the
    values need to be shifted to match any "hidden" rotations on any page.
    The `box` argument is a 4-tuple of left, bottom, right, top values."""
    def rotate_ninety_degrees_clockwise(box, n):
        """The `n` here is the number of 90deg rotations to do."""
        if n == 0:
            return box
        box = rotate_ninety_degrees_clockwise(box, n-1)
        return [box[1], box[2], box[3], box[0]]

    # These are for clockwise, swap do and undo to reverse.
    do_map = {0: 0, 90: 1, 180: 2, 270: 3} # Map angle to num of 90deg rotations.
    undo_map = {0: 0, 90: 3, 180: 2, 270: 1}

    if not undo:
        return rotate_ninety_degrees_clockwise(box, do_map[angle])
    else:
        return rotate_ninety_degrees_clockwise(box, undo_map[angle])

def get_full_page_box_assigning_media_and_crop(page):
    """This returns whatever PDF box was selected (by the user option
    '--fullPageBox') to represent the full page size.  All cropping is done
    relative to this box.  The default selection option is the MediaBox
    intersected with the CropBox so multiple crops work as expected.

    The argument page should be a pyPdf page object.

    This function also sets the MediaBox and CropBox of the page to the
    full-page size and saves the old values in the same page namespace, so it
    should only be called once for each page.  It returns a `RectangleObject`
    box."""

    # Find the page rotation angle (degrees).
    # Note rotation is clockwise, and four values are allowed: 0 90 180 270
    rotation = page.rotation
    while rotation >= 360:
        rotation -= 360
    while rotation < 0:
        rotation += 360

    # Save the rotation value in the page's namespace so we can restore it later.
    page.rotationAngle = rotation

    # Un-rotate the page, to a rotation of 0.
    page.set_rotation(0)

    # Save copies of some values in the page's namespace, to possibly restore later.
    page.original_media_box = get_box(page, "mediabox")
    page.original_crop_box = get_box(page, "cropbox")

    box_string = ["m", "c"]

    first_loop = True
    for box_string in args.fullPageBox:
        if box_string == "m":
            f_box = get_box(page, "mediabox")
        if box_string == "c":
            f_box = get_box(page, "cropbox")
        if box_string == "t":
            f_box = get_box(page, "trimbox")
        if box_string == "a":
            f_box = get_box(page, "artbox")
        if box_string == "b":
            f_box = get_box(page, "bleedbox")

        # Take intersection over all chosen boxes.
        if first_loop:
            full_box = f_box
        else:
            full_box = intersect_pdf_boxes(full_box, f_box, page)

        first_loop = False

    return rotation, full_box, page

def apply_precrop(rotation, full_box, page):
    """Apply the precrop to the document's box settings."""
    # Do any absolute pre-cropping specified for the page (after modifying any
    # absolutePreCrop4 arguments to take into account rotations to the page).
    precrop_box = mod_box_for_rotation(args.absolutePreCrop4, rotation)

    full_box = [float(full_box[0]) + precrop_box[0],
                float(full_box[1]) + precrop_box[1],
                float(full_box[2]) - precrop_box[2],
                float(full_box[3]) - precrop_box[3],
                ]

    # Note that MediaBox is set FIRST, since PyMuPDF will reset all other boxes
    # when it is set.
    set_box(page, "mediabox", full_box)
    set_box(page, "cropbox", full_box)
    return full_box

def get_full_page_box_list_assigning_media_and_crop(input_doc_mupdf_wrapper, quiet=False):
    """Get a list of all the full-page box values for each page.  The boxes on
    the list are in the simple 4-float list format used by this program, not
    `RectangleObject` format."""

    full_page_box_list = []
    rotation_list = []

    if args.verbose and not quiet:
        print(f"\nOriginal full page sizes (rounded to "
              f"{DECIMAL_PRECISION_FOR_MARGIN_POINT_VALUES} digits) in PDF format (lbrt):")

    for page_num in range(input_doc_mupdf_wrapper.num_pages):

        # Get the current page and find the full-page box.
        curr_page = input_doc_mupdf_wrapper.page_list[page_num]
        rotation, full_box, page = get_full_page_box_assigning_media_and_crop(curr_page)

        # Do any absolute pre-cropping specified for the page (after modifying any
        # absolutePreCrop4 arguments to take into account rotations to the page).
        full_page_box = apply_precrop(rotation, full_box, page)

        if args.verbose and not quiet:
            # want to display page num numbering from 1, so add one
            rounded_box_string = ", ".join([str(round(f,
                        DECIMAL_PRECISION_FOR_MARGIN_POINT_VALUES)) for f in full_page_box])
            print(f"\t{str(page_num+1)}   rot = "
                  f"{curr_page.rotationAngle}  \t [{rounded_box_string}]")

        # Convert the `RectangleObject` to floats in an ordinary list and append.
        ordinary_box = [float(b) for b in full_page_box]
        full_page_box_list.append(ordinary_box)

        # Append the rotation value to the rotation_list.
        rotation_list.append(curr_page.rotationAngle)

    return full_page_box_list, rotation_list

def calculate_crop_list(full_page_box_list, bounding_box_list, angle_list,
                                                               page_nums_to_crop):
    """Given a list of full-page boxes (media boxes) and a list of tight
    bounding boxes for each page, calculate and return another list giving the
    list of bounding boxes to crop down to.  The parameter `angle_list` is
    a list of rotation angles which correspond to the pages.  The pages
    selected to crop are in the set `page_nums_to_crop`."""

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
    # is only applied to the pages in the set `page_nums_to_crop`.

    order_n = 0
    if args.samePageSizeOrderStat:
        args.samePageSize = True
        order_n = min(args.samePageSizeOrderStat[0], num_pages_to_crop - 1)
        order_n = max(order_n, 0)

    if args.samePageSize:
        if args.verbose:
            print("\nSetting each page size to the smallest box bounding all the pages.")
            if order_n != 0:
                print("But ignoring the largest {} pages in calculating each edge."
                        .format(order_n))

        same_size_bounding_box = [
              # We want the smallest of the left and bottom edges.
              sorted(full_page_box_list[pg][0] for pg in page_nums_to_crop),
              sorted(full_page_box_list[pg][1] for pg in page_nums_to_crop),
              # We want the largest of the right and top edges.
              sorted((full_page_box_list[pg][2] for pg in page_nums_to_crop), reverse=True),
              sorted((full_page_box_list[pg][3] for pg in page_nums_to_crop), reverse=True)
              ]
        same_size_bounding_box = [sortlist[order_n] for sortlist in same_size_bounding_box]

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

        if args.uniform:
            uniform_set_with_even_odd = True
        else:
            uniform_set_with_even_odd = False

        # Recurse on even and odd pages, after resetting some options.
        if args.verbose:
            print("\nRecursively calculating crops for even and odd pages.")
        args.evenodd = False # Avoid infinite recursion.
        args.uniform = True  # --evenodd implies uniform, just on each separate group
        even_crop_list, delta_page_nums_even = calculate_crop_list(full_page_box_list, bounding_box_list,
                                                                   angle_list, even_page_nums_to_crop)
        odd_crop_list, delta_page_nums_odd = calculate_crop_list(full_page_box_list, bounding_box_list,
                                                                 angle_list, odd_page_nums_to_crop)

        # Recombine the even and odd pages.
        combine_even_odd = []
        for p_num in page_range:
            if p_num % 2 == 0:
                combine_even_odd.append(even_crop_list[p_num])
            else:
                combine_even_odd.append(odd_crop_list[p_num])

        combine_delta_crop_list = [(delta_page_nums_even[i], delta_page_nums_odd[i])
                                   for i in range(4)]

        # Handle the case where --uniform was set with --evenodd.
        if uniform_set_with_even_odd:
            min_bottom_margin = min(box[1] for p_num, box in enumerate(combine_even_odd)
                                                          if p_num in page_nums_to_crop)
            max_top_margin = max(box[3] for p_num, box in enumerate(combine_even_odd)
                                                       if p_num in page_nums_to_crop)
            combine_even_odd = [[box[0], min_bottom_margin, box[2], max_top_margin]
                              for box in combine_even_odd]
        return combine_even_odd, combine_delta_crop_list

    # Before calculating the crops we modify the percentRetain and
    # absoluteOffset values for all the pages according to any specified.
    # rotations for the pages.  This is so, for example, uniform cropping is
    # relative to what the user actually sees.
    rotated_percent_retain = [mod_box_for_rotation(args.percentRetain4, angle_list[m_val])
                                                         for m_val in range(num_pages)]
    rotated_absolute_offset = [mod_box_for_rotation(args.absoluteOffset4, angle_list[m_val])
                                                         for m_val in range(num_pages)]

    # Calculate the list of deltas to be used to modify the original page
    # sizes.  Basically, a delta is the absolute diff between the full and
    # tight-bounding boxes, scaled according to the user's percentRetain, with
    # any absolute offset then added (lb) or subtracted (tr) as appropriate.
    #
    # The deltas are all positive unless absoluteOffset changes that or
    # percent>100 or percent<0.  They are added (lb) or subtracted (tr) as
    # appropriate.

    delta_list = []
    for p_num, (b_box, f_box) in enumerate(zip(bounding_box_list, full_page_box_list)):
        # Calculate margin percentages.
        pct_fracs = [rotated_percent_retain[p_num][m_val] / 100.0 for m_val in range(4)]
        deltas = [abs(b_box[m_val] - f_box[m_val]) for m_val in range(4)]
        if not args.percentText:
            adj_deltas = [deltas[m_val] * (1.0-pct_fracs[m_val]) for m_val in range(4)]
        else:
            text_size = (b_box[2]-b_box[0], b_box[3]-b_box[1], # Text size for each margin.
                         b_box[2]-b_box[0], b_box[3]-b_box[1])
            adj_deltas = [deltas[m_val] - text_size[m_val] * pct_fracs[m_val]
                                                                 for m_val in range(4)]

        # Calculate absolute offsets.
        adj_deltas = [adj_deltas[m_val] + rotated_absolute_offset[p_num][m_val]
                                                           for m_val in range(4)]
        delta_list.append(adj_deltas)

    # Handle the '--uniform' options if one was selected.
    if args.uniformOrderPercent:
        percent_val = args.uniformOrderPercent[0]
        if percent_val < 0.0:
            percent_val = 0.0
        if percent_val > 100.0:
            percent_val = 100.0
        args.uniformOrderStat4 = [int(round(num_pages_to_crop * percent_val / 100.0))] * 4

    # Expand to tuples containing page nums, to better print verbose information.
    delta_list_paged = [(delta_list[j], j+1) for j in page_range] # Note +1 added here.

    # Only look at the deltas which correspond to pages selected for cropping.
    # The values will then be sorted for each margin and selected.
    crop_delta_list_paged = [delta_list_paged[j] for j in page_range if j in page_nums_to_crop]

    # Get a sorted list of (delta, page_num) tuples for each margin.  This is used
    # for orderstat calculations as well as for verbose information in the general case.
    # Note that we only sort over the page_nums_to_crop instead of all pages.
    sorted_left_vals = sorted([(pl[0][0], pl[1]) for pl in crop_delta_list_paged])
    sorted_lower_vals = sorted([(pl[0][1], pl[1]) for pl in crop_delta_list_paged])
    sorted_right_vals = sorted([(pl[0][2], pl[1]) for pl in crop_delta_list_paged])
    sorted_upper_vals = sorted([(pl[0][3], pl[1]) for pl in crop_delta_list_paged])

    if args.cropSafe:
        ignored_pages_left = {p for p in range(num_pages) if p not in page_nums_to_crop}
        ignored_pages_lower = {p for p in range(num_pages) if p not in page_nums_to_crop}
        ignored_pages_right = {p for p in range(num_pages) if p not in page_nums_to_crop}
        ignored_pages_upper = {p for p in range(num_pages) if p not in page_nums_to_crop}

    if args.uniform or args.uniformOrderStat4:
        if args.verbose:
            print("\nAll the selected pages will be uniformly cropped.")
        # Handle order stats; m_values are the four index values into the sorted
        # delta lists, one per margin.
        m_values = [0, 0, 0, 0]
        if args.uniformOrderStat4:
            m_values = args.uniformOrderStat4
        bounded_m_values = []
        for m_val in m_values:
            if m_val < 0 or m_val >= num_pages_to_crop:
                print("\nWarning: The selected order statistic is out of range.",
                      "Setting to closest value.", file=sys.stderr)
                if m_val >= num_pages_to_crop:
                    m_val = num_pages_to_crop - 1
                if m_val < 0:
                    m_val = 0
            bounded_m_values.append(m_val)
        m_values = bounded_m_values

        if args.cropSafe:
            skip_pages_left = set(sorted_left_vals[:m_values[0]])
            skip_pages_lower = set(sorted_lower_vals[:m_values[1]])
            skip_pages_right = set(sorted_right_vals[:m_values[2]])
            skip_pages_upper = set(sorted_upper_vals[:m_values[3]])
            # Here we convert the +1 pages meant for display into internal 0-based page numbers.
            if skip_pages_left:
                skip_pages_left = {d[1] - 1 for d in skip_pages_left}
            if skip_pages_lower:
                skip_pages_lower = {d[1] - 1 for d in skip_pages_lower}
            if skip_pages_right:
                skip_pages_right = {d[1] - 1 for d in skip_pages_right}
            if skip_pages_upper:
                skip_pages_upper = {d[1] - 1 for d in skip_pages_upper}
            ignored_pages_left |= skip_pages_left
            ignored_pages_lower |= skip_pages_lower
            ignored_pages_right |= skip_pages_right
            ignored_pages_upper |= skip_pages_upper

        if args.verbose and (args.uniformOrderPercent or args.uniformOrderStat4):
            print("\nPer-margin, the", m_values,
                  "smallest delta values over the selected pages\nwill be ignored"
                  " when choosing common, uniform delta values.")

        delta_list = [[sorted_left_vals[m_values[0]][0], sorted_lower_vals[m_values[1]][0],
                      sorted_right_vals[m_values[2]][0], sorted_upper_vals[m_values[3]][0]]] * num_pages

        delta_page_nums = [sorted_left_vals[m_values[0]][1], sorted_lower_vals[m_values[1]][1],
                           sorted_right_vals[m_values[2]][1], sorted_upper_vals[m_values[3]][1]]
        if args.verbose:
            print("\nThe smallest delta values actually used to set the uniform"
                  " cropping\namounts (ignoring any '-m' skips and pages in ranges"
                  " not cropped) were\nfound on these pages, numbered from 1:\n   ",
                  delta_page_nums)
            print("\nThe final delta values themselves are:\n   ", delta_list_paged[0])
    else: # Use the smallest, leftmost sorted value for the non-uniform case.
        delta_page_nums = [sorted_left_vals[0][1], sorted_lower_vals[0][1],
                           sorted_right_vals[0][1], sorted_upper_vals[0][1]]

    if args.keepHorizCenter:
        delta_list = [(min(d[0],d[2]), d[1], min(d[0],d[2]), d[3])
                      for p, d in enumerate(delta_list) if p in page_nums_to_crop]

    if args.keepVertCenter:
        delta_list = [(d[0], min(d[1],d[3]), d[2], min(d[1],d[3]))
                      for p, d in enumerate(delta_list) if p in page_nums_to_crop]

    # Apply the delta modifications to the full boxes to get the final sizes.
    final_crop_list = []
    for f_box, deltas in zip(full_page_box_list, delta_list):
        final_crop_list.append((f_box[0] + deltas[0], f_box[1] + deltas[1],
                                f_box[2] - deltas[2], f_box[3] - deltas[3]))

    if args.cropSafe:
        safe_final_crop_list = []
        csm0, csm1, csm2, csm3 = args.cropSafeMin4
        for page, (final_crops, bounding_box) in enumerate(zip(final_crop_list, bounding_box_list)):
            final_crops = list(final_crops)
            if page not in ignored_pages_left and final_crops[0] > bounding_box[0]-csm0:
                final_crops[0] = bounding_box[0]-csm0
            if page not in ignored_pages_lower and final_crops[1] > bounding_box[1]-csm1:
                final_crops[1] = bounding_box[1]-csm1
            if page not in ignored_pages_right and final_crops[2] < bounding_box[2]+csm2:
                final_crops[2] = bounding_box[2]+csm2
            if page not in ignored_pages_upper and final_crops[3] < bounding_box[3]+csm3:
                final_crops[3] = bounding_box[3]+csm3
            safe_final_crop_list.append(tuple(final_crops))
        if args.uniform or args.uniformOrderStat4:
            sfcl = safe_final_crop_list # Shorter alias for below.
            final_crop_list = [(min(sfcl[p][0] for p in page_nums_to_crop if p not in ignored_pages_left),
                                min(sfcl[p][1] for p in page_nums_to_crop if p not in ignored_pages_lower),
                                max(sfcl[p][2] for p in page_nums_to_crop if p not in ignored_pages_right),
                                max(sfcl[p][3] for p in page_nums_to_crop if p not in ignored_pages_upper)
                               )] * num_pages
        else:
            final_crop_list = safe_final_crop_list

    # Set the page ratios if user chose that option.
    if args.setPageRatios:
        ratio = args.setPageRatios
        left_weight, bottom_weight, right_weight, top_weight = args.pageRatioWeights
        if args.verbose:
            print("\nSetting all page width to height ratios to:", ratio)
            print("The weights per margin are:",
                    left_weight, bottom_weight, right_weight, top_weight)
        ratio_set_crop_list = []
        for pnum, (left, bottom, right, top) in enumerate(final_crop_list):
            if pnum not in page_nums_to_crop:
                ratio_set_crop_list.append((left, bottom, right, top))
                continue
            # Pad out left/right or top/bottom margins; padding amount is scaled.
            width = right - left
            height = top - bottom
            new_height = width / ratio
            if new_height < height: # Use new_width instead.
                new_width = height * ratio
                assert new_width >= width
                difference = new_width - width
                total_lr_weight = left_weight + right_weight
                left_weight /= total_lr_weight
                right_weight /= total_lr_weight
                ratio_set_crop_list.append((left - difference * left_weight, bottom,
                                            right + difference * right_weight, top))
            else:
                difference = new_height - height
                total_tb_weight = bottom_weight + top_weight
                bottom_weight /= total_tb_weight
                top_weight /= total_tb_weight
                ratio_set_crop_list.append((left, bottom - difference * bottom_weight,
                                           right, top + difference * top_weight))
        final_crop_list = ratio_set_crop_list

    return final_crop_list, delta_page_nums

def check_and_set_crop_metadata(document_wrapper_class, metadata_info):
    """First check the producer metadata attribute to see if this program was
    cropped document before.  Returns the variable
    `already_cropped_by_this_program` which is either `False` or has the value
    string `"<2.0"` or `">=2.0".

    The "Producer" metadata then has a string appended (if not already there)
    to indicate that this program modified the file."""
    def has_xml_restore_data():
        """This function is a workaround because setting the XML metadata key
        to "null" doesn't seem to delete the key itself like the docs say.  Need
        to look at the value to determine if there is data there to determine
        `already_cropped_by_this_program` since value is set null on restore."""
        # TODO: Should be able to just check key with `doc_wrap.has_xml_metadata_key`
        # but doesn't work.
        data_value, has_xml_metadata, has_key = document_wrapper_class.get_xml_metadata_value(
                                                                         RESTORE_METADATA_KEY)
        if has_key:
            return data_value[0] == "["
        return False

    if metadata_info:
        old_producer_string = metadata_info["producer"]
    else:
        return PRODUCER_MODIFIER, False # Can't read metadata, but maybe can set it.

    if has_xml_restore_data(): # See note in function.
        if args.verbose:
            print("\nThe document was already cropped at least once by pdfCropMargins>=2.0.")
        already_cropped_by_this_program = ">=2.0"

    elif old_producer_string and old_producer_string.endswith(PRODUCER_MODIFIER):
        if args.verbose:
            print("\nThe document was already cropped at least once by pdfCropMargins<2.0.")
        already_cropped_by_this_program = "<2.0"
        # Update the Producer suffix to the the new PRODUCER_MODIFIER_2.
        new_producer_string = old_producer_string.replace(PRODUCER_MODIFIER, PRODUCER_MODIFIER_2)
        metadata_info["producer"] = new_producer_string

    else:
        if args.verbose:
            print("\nThe document was not previously cropped by pdfCropMargins.")
        metadata_info["producer"] = metadata_info["producer"] + PRODUCER_MODIFIER_2
        already_cropped_by_this_program = False

    document_wrapper_class.set_standard_metadata(metadata_info)
    return already_cropped_by_this_program

def serialize_boxlist(boxlist):
    """Return the string for the list of boxes."""
    return str([list(b) for b in boxlist])

def deserialize_boxlist(boxlist_string):
    """Return the string for the list of boxes."""
    if boxlist_string[0] != "[" or boxlist_string[-1] != "]":
        return None
    boxlist_string = boxlist_string[2:-2]
    split_list = boxlist_string.split("], [")
    deserialized_boxlist = []
    for box in split_list:
        values = box.split(",")
        try:
            deserialized_boxlist.append([float(v) for v in values])
        except ValueError:
            return None
    return deserialized_boxlist

def save_old_boxes_for_restore(input_doc_mupdf_wrapper, original_mediabox_list,
                               original_cropbox_list, original_artbox_list,
                               already_cropped_by_this_program):
    """Save the intersection of the cropbox and the mediabox."""
    if already_cropped_by_this_program == "<2.0":
        old_boxes_to_save_list = original_artbox_list
    else:
        old_boxes_to_save_list = [] # Save list of old boxes to possibly save for later restore.
        for page_num in range(input_doc_mupdf_wrapper.document.page_count):
            curr_page = input_doc_mupdf_wrapper.page_list[page_num]

            # Do the save for later restore if that option is chosen and Producer is not set.
            box = intersect_pdf_boxes(original_mediabox_list[page_num],
                                      original_cropbox_list[page_num], curr_page)
            old_boxes_to_save_list.append(box)

    serialized_saved_boxes_list = serialize_boxlist(old_boxes_to_save_list)
    input_doc_mupdf_wrapper.set_xml_metadata_item(RESTORE_METADATA_KEY,
                                                        serialized_saved_boxes_list)

def apply_crop_list(crop_list, input_doc_mupdf_wrapper, page_nums_to_crop,
                    already_cropped_by_this_program):
    """Apply the crop list to the pages of the input document."""
    if args.writeCropDataToFile:
        args.writeCropDataToFile = ex.get_expanded_path(args.writeCropDataToFile)
        f = open(args.writeCropDataToFile, "w")
    else:
        f = None

    if args.verbose:
        print("\nNew full page sizes after cropping, in PDF format (lbrt):")

    # Set the appropriate PDF boxes on each page.
    for page_num in range(input_doc_mupdf_wrapper.document.page_count):
        curr_page = input_doc_mupdf_wrapper.page_list[page_num]

        # Restore any rotation which was originally on the page.
        curr_page.set_rotation(curr_page.rotationAngle)

        # Reset the CropBox and MediaBox to their saved original values (they
        # were saved by `get_full_page_box_assigning_media_and_crop` in the
        # `curr_page` object's namespace).  Restore the MediaBox and CropBox to
        # the saved values.  Note that MediaBox is set FIRST, since PyMuPDF
        # will reset all other boxes when it is set.
        set_box(curr_page, "mediabox", curr_page.original_media_box)
        set_box(curr_page, "cropbox", curr_page.original_crop_box)

        # Copy the original page without further mods if it wasn't in the range
        # selected for cropping.
        if page_num not in page_nums_to_crop:
            continue

        rounded_values = [round(f, DECIMAL_PRECISION_FOR_MARGIN_POINT_VALUES)
                                for f in crop_list[page_num]]
        new_cropped_box = rounded_values

        if args.verbose:
            print("\t"+str(page_num+1)+"\t", list(new_cropped_box)) # page numbering from 1
        if args.writeCropDataToFile:
            print("\t"+str(page_num+1)+"\t", list(new_cropped_box), file=f)

        if not args.boxesToSet:
            args.boxesToSet = ["m", "c"]

        # Now set any boxes which were selected to be set via the '--boxesToSet' option.
        if "m" in args.boxesToSet:
            # Note the MediaBox is always set FIRST, since it resets the other boxes.
            set_box(curr_page, "mediabox", new_cropped_box)
        if "c" in args.boxesToSet:
            set_box(curr_page, "cropbox", new_cropped_box)
        if "t" in args.boxesToSet:
            set_box(curr_page, "trimbox", new_cropped_box)
        if "a" in args.boxesToSet:
            set_box(curr_page, "artbox", new_cropped_box)
        if "b" in args.boxesToSet:
            set_box(curr_page, "bleedbox", new_cropped_box)

    if args.writeCropDataToFile:
        f.close()
        ex.cleanup_and_exit(0)

def apply_restore_operation(already_cropped_by_this_program, input_doc_mupdf_wrapper,
                            original_artbox_list):
    """Restore the saved page boxes to the document."""
    if args.writeCropDataToFile:
        args.writeCropDataToFile = ex.get_expanded_path(args.writeCropDataToFile)
        f = open(args.writeCropDataToFile, "w")
    else:
        f = None

    if already_cropped_by_this_program == ">=2.0":
        saved_boxes, has_xml_metadata, xml_metadata_has_key = (
                input_doc_mupdf_wrapper.get_xml_metadata_value(RESTORE_METADATA_KEY))
        saved_boxes_list = deserialize_boxlist(saved_boxes)
        if not saved_boxes_list:
            print("\nError in pdfCropMargins: Could not deserialize the data saved for the"
                    "\nrestore operation.  Deleting the key and the data.", file=sys.stderr)
            input_doc_mupdf_wrapper.delete_xml_metadata_item(RESTORE_METADATA_KEY)

    elif already_cropped_by_this_program == "<2.0":
        saved_boxes_list = original_artbox_list

    if not saved_boxes_list or len(saved_boxes_list) != input_doc_mupdf_wrapper.num_pages:
        print("\nError in pdfCropMargins: The number of pages in the saved restore"
              "\ndata is not the same as the number of pages in the document.  The"
              "\nrestore operation will be ignored.", file=sys.stderr)
        return

    for page_num in range(input_doc_mupdf_wrapper.document.page_count):
        curr_page = input_doc_mupdf_wrapper.page_list[page_num]

        # Restore any rotation which was originally on the page.
        curr_page.set_rotation(curr_page.rotationAngle)

        # Restore the MediaBox and CropBox to the saved values.  Note that
        # MediaBox is set FIRST, since PyMuPDF will reset all other boxes
        # when it is set.
        set_box(curr_page, "mediabox", saved_boxes_list[page_num])
        set_box(curr_page, "cropbox", saved_boxes_list[page_num])
        if args.writeCropDataToFile:
            print("\t"+str(page_num+1)+"\t", saved_boxes_list[page_num], file=f)

    # The saved restore data is no longer needed.
    if args.verbose:
        print("\nDeleting the saved restore metadata since it is no longer needed.")
    input_doc_mupdf_wrapper.delete_xml_metadata_item(RESTORE_METADATA_KEY)

    if args.writeCropDataToFile:
        f.close()
        ex.cleanup_and_exit(0)

##############################################################################
#
# Functions implementing the major operations.
#
##############################################################################

def process_command_line_arguments(parsed_args, cmd_parser):
    """Perform an initial processing on the some of the command-line arguments.  This
    is called first, before any PDF processing is done."""
    global args # This is global to avoid passing it to essentially every function.
    args = parsed_args

    if args.prevCropped:
        args.gui = False # Ignore the GUI when --prevCropped option is selected.
        args.verbose = False # Wants to eval the text in Bash script.

    if args.verbose:
        print(f"\nProcessing the PDF with pdfCropMargins (version {__version__})...")
        print("Python version:", ex.python_version)
        print("System type:", ex.system_os)
        print(fitz.__doc__) # Print out PyMuPDF version info.

    if len(args.pdf_input_doc) > 1:
        print("\nError in pdfCropMargins: Only one input PDF document is allowed."
              "\nFound more than one on the command line:", file=sys.stderr)
        for f in args.pdf_input_doc:
            print("   ", f, file=sys.stderr)
        print(file=sys.stderr)
        if not args.prevCropped: # Because Bash script conditionals try to evaluate `usage` on fail.
            cmd_parser.print_usage()
        #cmd_parser.exit() # Exits whole program.
        ex.cleanup_and_exit(1)
    # Note: Below code currently handled by the argparse + option, not *, on pdf_input_doc.
    #elif len(args.pdf_input_doc) < 1:
    #    print("\nError in pdfCropMargins: No PDF document argument passed in.",
    #          file=sys.stderr)
    #    print()
    #    cmd_parser.print_usage()
    #    #cmd_parser.exit() # Exits whole program.
    #    ex.cleanup_and_exit(1)

    #
    # Process input and output filenames.
    #

    input_doc_path = args.pdf_input_doc[0]
    input_doc_path = ex.get_expanded_path(input_doc_path) # Expand vars and user.
    input_doc_path = ex.glob_pathname(input_doc_path, exact_num_args=1)[0]
    if not input_doc_path.endswith((".pdf",".PDF")):
        print("\nWarning in pdfCropMargins: The file extension is neither '.pdf'"
              "\nnor '.PDF'; continuing anyway.", file=sys.stderr)
    if args.verbose:
        print("\nThe input document's filename is:\n   ", input_doc_path)
    if not os.path.isfile(input_doc_path):
        print("\nError in pdfCropMargins: The specified input file\n   "
              + input_doc_path + "\nis not a file or does not exist.",
              file=sys.stderr)
        ex.cleanup_and_exit(1)

    if not args.outfile and args.verbose:
        print("\nUsing the default-generated output filename.")

    output_doc_path = generate_output_filepath(input_doc_path)
    if args.verbose:
        print("\nThe output document's filename will be:\n   ", output_doc_path)

    if os.path.lexists(output_doc_path) and args.noclobber:
        # Note lexists above, don't overwrite broken symbolic links, either.
        print("\nOption '--noclobber' is set, refusing to overwrite an existing"
              "\nfile with filename:\n   ", output_doc_path, file=sys.stderr)
        ex.cleanup_and_exit(1)

    if os.path.lexists(output_doc_path) and ex.samefile(input_doc_path,
                                                                output_doc_path):
        print("\nError in pdfCropMargins: The input file is the same as"
              "\nthe output file.\n", file=sys.stderr)
        ex.cleanup_and_exit(1)

    #
    # Process some args with both regular and per-page 4-param forms.  Note that
    # in all these cases the 4-param version takes precedence.
    #

    if args.absolutePreCrop and not args.absolutePreCrop4:
        args.absolutePreCrop4 = args.absolutePreCrop * 4 # expand to 4 offsets
    if args.verbose:
        print("\nThe absolute pre-crops to be applied to each margin, in units of bp,"
              " are:\n   ", args.absolutePreCrop4)

    if args.percentRetain and not args.percentRetain4:
        args.percentRetain4 = args.percentRetain * 4 # expand to 4 percents
    # See if all four percents are explicitly set and use those if so.
    if args.verbose:
        print("\nThe percentages of margins to retain are:\n   ",
              args.percentRetain4)

    if args.absoluteOffset and not args.absoluteOffset4:
        args.absoluteOffset4 = args.absoluteOffset * 4 # expand to 4 offsets
    if args.verbose:
        print("\nThe absolute offsets to be applied to each margin, in units of bp,"
              " are:\n   ", args.absoluteOffset4)

    # TODO: Note that these verbose messages are NOT printed when the GUI is used, since
    # the processing only calls process_pdf_file.  Similarly, range checks and repairs
    # for uniformOrderStat are not processed when entered directly into the GUI.
    if args.uniformOrderStat and not args.uniformOrderStat4:
        args.uniformOrderStat4 = args.uniformOrderStat * 4 # expand to 4 offsets
    if args.verbose:
        print("\nThe uniform order statistics to apply to each margin, in units of bp,"
              " are:\n   ", args.uniformOrderStat4)

    #
    # Process page ratios.
    #

    if args.setPageRatios and not args.gui: # GUI does its own parsing.
        # Parse the page ratio into a float if user chose that representation.
        ratio_arg = args.setPageRatios
        try:
            float_ratio = parse_page_ratio_argument(ratio_arg)
        except ValueError:
            ex.cleanup_and_exit(1) # Parse fun printed error message.
        args.setPageRatios = float_ratio

    if args.pageRatioWeights:
        for w in args.pageRatioWeights:
            if w <= 0:
                print("\nError in pdfCropMargins: Negative weight argument passed "
                      "to pageRatiosWeights.", file=sys.stderr)
                ex.cleanup_and_exit(1)

    #
    # Process options dealing with rendering and external programs.
    #

    if args.gsRender:
        args.calcbb = "gr" # Backward compat.
        warn("\nThe --gsRender option is deprecated and will be removed in "
                "version 3.0.  Use '-c gr' instead.", DeprecationWarning, 2)
    if args.gsBbox:
        warn("\nThe --gsBbox option is deprecated and will be removed in "
                "version 3.0.  Use '-c gb' instead.", DeprecationWarning, 2)
        args.calcbb = "gb" # Backward compat.
    if args.calcbb == "m" and not has_mupdf:
        print("Error in pdfCropMargins: The option '--calcbb m' was selected"
              "\nbut PyMuPDF (at least v1.14.5) was not installed in Python."
              "\nInstalling pdfCropMargins with the GUI option will include that"
              "\ndependency.", file=sys.stderr)
        ex.cleanup_and_exit(1)
    if args.calcbb == "d" and has_mupdf:
        args.calcbb = "m" # Default to PyMuPDF.
    elif args.calcbb == "d": # Rendering without PyMuPDF.
        args.calcbb = "o"     # Revert to old method.

    if args.calcbb == "gb" and len(args.fullPageBox) > 1:
        print("\nWarning: only one --fullPageBox value can be used with the '--calcbb gb'"
              "\nor '--gsBbox' option. Ignoring all but the first one.", file=sys.stderr)
        args.fullPageBox = [args.fullPageBox[0]]
    elif args.calcbb == "gb" and not args.fullPageBox:
        args.fullPageBox = ["c"] # gs default
    elif not args.fullPageBox:
        args.fullPageBox = ["m", "c"] # usual default

    if args.verbose:
        print("\nFor the full page size, using values from the PDF box"
              "\nspecified by the intersection of these boxes:", args.fullPageBox)

    # Set executable paths to non-default locations if set.
    if args.pdftoppmPath:
        ex.set_pdftoppm_executable_to_string(args.pdftoppmPath)
    if args.ghostscriptPath:
        ex.set_gs_executable_to_string(args.ghostscriptPath)

    # If the option settings require pdftoppm, make sure we have a running version.
    gs_render_fallback_set = False # Set True if we switch to gs option as a fallback.
    if args.calcbb in ["p", "o"]:
        # Note that after this block, the `--calcbb o` option is converted to 'p' or 'gr'.
        found_pdftoppm = ex.init_and_test_pdftoppm_executable(
                                                   prefer_local=args.pdftoppmLocal)
        if args.verbose:
            print("\nFound pdftoppm program at:", found_pdftoppm)
        if found_pdftoppm:
            args.calcbb = "p"
        elif args.calcbb == "p":
                print("\nError in pdfCropMargins: The '--calcbb p' option was specified "
                      "\nbut the pdftoppm executable could not be located.  Is it"
                      "\ninstalled and in the PATH for command execution?\n",
                      file=sys.stderr)
                ex.cleanup_and_exit(1)
        else:
            # Try fallback to gs.
            gs_render_fallback_set = True
            args.calcbb = "gr"
            if args.verbose:
                print("\nNo pdftoppm executable found; using Ghostscript for rendering.")

    # If any options require Ghostscript, make sure it is installed.
    if args.calcbb == "gr" or args.calcbb == "gb" or args.gsFix:
        found_gs = ex.init_and_test_gs_executable()
        if args.verbose:
            print("\nFound Ghostscript program at:", found_gs)
    if args.calcbb == "gb" and not found_gs:
        print("\nError in pdfCropMargins: The '--calcbb gb' or '--gsBbox' option was"
              "\nspecified but the Ghostscript executable could not be located.  Is it"
              "\ninstalled and in the PATH for command execution?\n", file=sys.stderr)
        ex.cleanup_and_exit(1)
    if args.gsFix and not found_gs:
        print("\nError in pdfCropMargins: The '--gsFix' option was specified but"
              "\nthe Ghostscript executable could not be located.  Is it"
              "\ninstalled and in the PATH for command execution?\n", file=sys.stderr)
        ex.cleanup_and_exit(1)
    if (args.calcbb == "gr" or gs_render_fallback_set) and not found_gs:
        if gs_render_fallback_set:
            print("\nError in pdfCropMargins: Neither Ghostscript nor pdftoppm"
                  "\nwas found in the PATH for command execution.  At least one is"
                  "\nrequired without PyMuPDF installed.\n", file=sys.stderr)
        else:
            print("\nError in pdfCropMargins: The '--calcbb gr' or the '--gsRender' option"
                  "\nwas specified but the Ghostscript executable could not be located.  Is "
                  "\nit installed and in the PATH for command execution?\n", file=sys.stderr)
        ex.cleanup_and_exit(1)

    # Give a warning message if incompatible option combinations have been selected.
    if args.threshold[0] != DEFAULT_THRESHOLD_VALUE and args.calcbb == "gb":
            print("\nWarning in pdfCropMargins: The '--threshold' option is ignored"
                "\nwhen the '--calcbb gb' or '--gsBbox' option is also selected.\n",
                file=sys.stderr)
    if args.calcbb == "gb" and args.numBlurs:
        print("\nWarning in pdfCropMargins: The '--numBlurs' option is ignored"
              "\nwhen the '--calcbb gb' or '--gsBbox' option is also selected.\n",
              file=sys.stderr)
    if args.calcbb == "gb" and args.numSmooths:
        print("\nWarning in pdfCropMargins: The '--numSmooths' option is ignored"
              "\nwhen the '--calcbb gb' or '--gsBbox' option is also selected.\n",
              file=sys.stderr)

    if args.gsFix:
        if args.verbose:
            print("\nAttempting to fix the PDF input file before reading it...")
        fixed_input_doc_pathname = ex.fix_pdf_with_ghostscript_to_tmp_file(input_doc_path)
    else:
        fixed_input_doc_pathname = input_doc_path

    return input_doc_path, fixed_input_doc_pathname, output_doc_path

def open_file_in_pymupdf(fixed_input_doc_pathname):
    """Open the file in a `MuPdfDocument`."""
    input_doc_mupdf_wrapper = MuPdfDocument(args)
    input_doc_num_pages = input_doc_mupdf_wrapper.open_document(fixed_input_doc_pathname)

    if args.verbose:
        print(f"\nThe input document has {input_doc_num_pages} pages.")
        if input_doc_mupdf_wrapper.document.is_repaired:
            print("\nThe document was repaired by PyMuPDF on being read.")
        else:
            print("\nThe document was not repaired by PyMuPDF on being read.")

    # Note this is only the standard metadata, not any additional metadata like
    # any restore metadata.
    metadata_info = input_doc_mupdf_wrapper.get_standard_metadata()

    if args.verbose and not metadata_info:
        print("\nNo readable metadata in the document.")
    elif args.verbose:
        try:
            print("\nThe document's metadata, if set:\n")
            print("   The Author attribute set in the input document is:\n      %s"
                  % (metadata_info["author"]))
            print("   The Creator attribute set in the input document is:\n      %s"
                  % (metadata_info["creator"]))
            print("   The Producer attribute set in the input document is:\n      %s"
                  % (metadata_info["producer"]))
            print("   The Subject attribute set in the input document is:\n      %s"
                  % (metadata_info["subject"]))
            print("   The Title attribute set in the input document is:\n      %s"
                  % (metadata_info["title"]))
        except (KeyError, UnicodeDecodeError, UnicodeEncodeError):
            print("\nWarning: Could not write all the document's metadata to the screen."
                  "\nGot a KeyError or a UnicodeEncodeError.", file=sys.stderr)

    return input_doc_mupdf_wrapper, metadata_info, input_doc_num_pages

def get_set_of_page_numbers_to_crop(input_doc_num_pages):
    """Compute the set containing the page number of all the pages
    which the user has selected for cropping from the command line."""
    all_page_nums = set(range(0, input_doc_num_pages))
    if args.pages:
        try:
            page_nums_to_crop = parse_page_range_specifiers(args.pages, all_page_nums)
        except ValueError:
            print(
                "\nError in pdfCropMargins: The page range specified on the command",
                "\nline contains a non-integer value or otherwise cannot be parsed.",
                file=sys.stderr)
            ex.cleanup_and_exit(1)
    else:
        page_nums_to_crop = all_page_nums

    # In verbose mode print out information about the pages to crop.
    if args.verbose and args.pages:
        print("\nThese pages of the document will be cropped:", end="")
        p_num_list = sorted(list(page_nums_to_crop))
        num_pages_to_crop = len(p_num_list)
        for i in range(num_pages_to_crop):
            if i % 10 == 0 and i != num_pages_to_crop - 1:
                print("\n   ", end="")
            print("%5d" % (p_num_list[i]+1), " ", end="")
        print()
    elif args.verbose:
        print("\nAll the pages of the document will be cropped.")
    return page_nums_to_crop

def process_pdf_file(input_doc_pathname, fixed_input_doc_pathname, output_doc_pathname,
                     bounding_box_list=None):
    """This function does the real work.  It is called by `main()` in
    `pdfCropMargins.py`, which just handles catching exceptions and cleaning
    up.

    If a bounding box list is passed in then the bounding box calculation is
    skipped and that list is used instead (for cases with the GUI when the
    boxes do not change but the cropping does).

    Returns the bounding box list and data about the minimum cropping deltas
    for each margins."""

    input_doc_mupdf_wrapper, metadata_info, input_doc_num_pages = open_file_in_pymupdf(
                                                                   fixed_input_doc_pathname)

    # Get any necessary page boxes BEFORE the MediaBox is set.  The pyMuPDF
    # program will reset the other boxes when setting the MediaBox if they're
    # not fully contained.  For the ArtBox this is for backward compatibility
    # with the earlier PyPDF restore option.
    original_mediabox_list = input_doc_mupdf_wrapper.get_box_list("mediabox")
    original_cropbox_list = input_doc_mupdf_wrapper.get_box_list("cropbox")
    original_artbox_list = input_doc_mupdf_wrapper.get_box_list("artbox")
    #original_trimbox_list = input_doc_mupdf_wrapper.get_box_list("trimbox")
    #original_bleedbox_list = input_doc_mupdf_wrapper.get_box_list("bleedbox")

    already_cropped_by_this_program = check_and_set_crop_metadata(input_doc_mupdf_wrapper,
                                                                  metadata_info)

    if not args.noundosave:
        if already_cropped_by_this_program == "<2.0" or not already_cropped_by_this_program:
            save_old_boxes_for_restore(input_doc_mupdf_wrapper, original_mediabox_list,
                                       original_cropbox_list, original_artbox_list,
                                       already_cropped_by_this_program)

    if args.prevCropped:
        input_doc_mupdf_wrapper.close_document()
        if already_cropped_by_this_program:
            #print("code 0")
            exit_code = 0
        else:
            #print("code 1")
            exit_code = 1
        ex.cleanup_and_exit(exit_code)

    # TODO: This doesn't work yet with GUI because GUI calls this fun only when cropping...
    #if args.exitPrevCropped and already_cropped_by_this_program:
    #    fixed_input_doc_file_object.close()
    #    if args.verbose:
    #        print("The file was previously cropped by pdfCropMargins, exiting.")
    #    ex.cleanup_and_exit(0)

    ##
    ## Now compute the set containing the page number of all the pages
    ## which the user has selected for cropping from the command line.  Most
    ## calculations are still carried out for all the pages in the document.
    ## (There are a few optimizations for expensive operations like finding
    ## bounding boxes; the rest is negligible).  This keeps the correspondence
    ## between page numbers and the positions of boxes in the box lists.  The
    ## function `apply_crop_list` then just ignores the cropping information
    ## for any pages which were not selected.
    ##

    page_nums_to_crop = get_set_of_page_numbers_to_crop(input_doc_num_pages)

    ##
    ## Get a list with the full-page boxes for each page: (left,bottom,right,top)
    ## This function also sets the MediaBox and CropBox of the pages to the
    ## chosen full-page size as a side-effect, saving the old boxes.  Any absolute
    ## pre-crop is also applied here (so it is rendered that way for the later
    ## bounding-box-finding operation).
    ##

    full_page_box_list, rotation_list = get_full_page_box_list_assigning_media_and_crop(
                                              input_doc_mupdf_wrapper)

    ##
    ## Write out the PDF document again, with the CropBox and MediaBox reset.
    ## This temp document version is ONLY used for calculating the bounding boxes of
    ## pages.
    ##

    if not args.restore:
        if not bounding_box_list:
            doc_with_crop_and_media_boxes_name = ex.get_temporary_filename(".pdf")
            if args.verbose:
                # TODO Consider writing this to a memory file rather than to disk.
                print("\nWriting out the PDF with the CropBox and MediaBox redefined"
                        "\n(so pre-crops are included in the bounding box calculations).")
            input_doc_mupdf_wrapper.save_document(doc_with_crop_and_media_boxes_name)

    ##
    ## Calculate the `bounding_box_list` containing tight page bounds for each page.
    ##

    if not args.restore:
        if not bounding_box_list:
            bounding_box_list = get_bounding_box_list(doc_with_crop_and_media_boxes_name,
                    input_doc_mupdf_wrapper, full_page_box_list, page_nums_to_crop, args)
            if args.verbose:
                print("\nThe bounding boxes are:")
                for pNum, b in enumerate(bounding_box_list):
                    print("\t", pNum+1, "\t", b)
            os.remove(doc_with_crop_and_media_boxes_name) # No longer needed.

        elif args.verbose:
            print("\nUsing the bounding box list passed in instead of calculating it.")

    ##
    ## Calculate the `crop_list` based on the fullpage boxes and the bounding boxes,
    ## after the precrop has been applied.
    ##

    if not args.restore:
        crop_list, delta_page_nums = calculate_crop_list(full_page_box_list, bounding_box_list,
                                        rotation_list, page_nums_to_crop)
    else:
        crop_list = None # Restore, not needed in this case.
        delta_page_nums = ("N/A","N/A","N/A","N/A")

    ##
    ## Apply the calculated crops to the pages (after restoring the original mediabox
    ## and cropbox).
    ##

    if args.restore:
        if args.verbose:
            print("\nRestoring the document to margins saved for each page.")

        if not already_cropped_by_this_program:
            print("\nWarning from pdfCropMargins: The Producer string and metadata indicate"
                  "\nthat either this document was not previously cropped by pdfCropMargins"
                  "\nor else it was modified by another program after that and cannot"
                  "\nbe restored.  Ignoring the restore operation.", file=sys.stderr)
        else:
            apply_restore_operation(already_cropped_by_this_program,
                                    input_doc_mupdf_wrapper, original_artbox_list)

    else:
        apply_crop_list(crop_list, input_doc_mupdf_wrapper, page_nums_to_crop,
                        already_cropped_by_this_program)

    ##
    ## Write the final PDF out to a file.
    ##

    input_doc_mupdf_wrapper.save_document(output_doc_pathname)
    input_doc_mupdf_wrapper.close_document()

    return bounding_box_list, delta_page_nums

def handle_options_on_cropped_file(input_doc_pathname, output_doc_pathname):
    """Handle the options which apply after the file is written such as previewing
    and renaming."""

    def do_preview(output_doc_pathname):
        viewer = args.preview
        if args.verbose:
            print("\nPreviewing the output document with viewer:\n   ", viewer)
        ex.show_preview(viewer, output_doc_pathname)
        return

    # Handle the '--queryModifyOriginal' option.
    if args.queryModifyOriginal:
        if args.preview:
            print("\nRunning the preview viewer on the file, will query whether or not"
                  "\nto modify the original file after the viewer is launched in the"
                  "\nbackground...\n")
            do_preview(output_doc_pathname)
            # Give preview time to start; it may write startup garbage to the terminal...
            query_wait_time = 2 # seconds
            time.sleep(query_wait_time)
            print()
        while True:
            query_string = "\nModify the original file to the cropped file " \
                "(saving the original)? [yn] "
            query_result = input(query_string).strip()
            if query_result in ["y", "Y"]:
                args.modifyOriginal = True
                print("\nModifying the original file.")
                break
            elif query_result in ["n", "N"]:
                print("\nNot modifying the original file.  The cropped file is saved"
                      " as:\n   {}".format(output_doc_pathname))
                args.modifyOriginal = False
                break
            else:
                print("Response must be in the set {y,Y,n,N}, none recognized.")
                continue

    # Handle the '--modifyOriginal' option.
    final_output_document_name = output_doc_pathname
    if args.modifyOriginal:
        # Generate the backup filename for the original, uncropped file.
        generated_uncropped_filepath = generate_output_filepath(input_doc_pathname,
                                                                is_cropped_file=False,
                                                                ignore_output_filename=True)

        # Remove any existing file with the name `generated_uncropped_filename` unless
        # the relevant noclobber option is set, or it isn't a file.
        if os.path.exists(generated_uncropped_filepath):
            if (os.path.isfile(generated_uncropped_filepath)
                    and not args.noclobberOriginal and not args.noclobber):
                if args.verbose:
                    print("\nRemoving the file\n   ", generated_uncropped_filepath)
                try:
                    os.remove(generated_uncropped_filepath)
                except OSError:
                    print("Removing the file {} failed.  Maybe a permission error?"
                          "\nFiles are as if option '--modifyOriginal' were not set."
                          .format(generated_uncropped_filepath))
                    args.modifyOriginal = False # Failed.
            else:
                print("\nA noclobber option is set or else not a file; refusing to"
                    " overwrite:\n   ", generated_uncropped_filepath,
                    "\nFiles are as if option '--modifyOriginal' were not set.",
                    file=sys.stderr)
                args.modifyOriginal = False # Failed.

        # Move the original file to the name for uncropped files.  Silently do nothing
        # if the file exists (should have been removed above).
        if not os.path.exists(generated_uncropped_filepath):
            if args.verbose: print("\nDoing a file move:\n   ", input_doc_pathname,
                                   "\nis moving to:\n   ", generated_uncropped_filepath)
            shutil.move(input_doc_pathname, generated_uncropped_filepath)

        # Move the cropped file to the original file's name.  Silently do nothing if
        # the file exists (should have been moved above).
        if not os.path.exists(input_doc_pathname):
            if args.verbose: print("\nDoing a file move:\n   ", output_doc_pathname,
                                   "\nis moving to:\n   ", input_doc_pathname)
            shutil.move(output_doc_pathname, input_doc_pathname)
            final_output_document_name = input_doc_pathname

    # Handle any previewing which still needs to be done.
    if args.preview and not args.queryModifyOriginal: # queryModifyOriginal does its own.
        do_preview(final_output_document_name)

    if args.verbose:
        print("\nFinished this run of pdfCropMargins.\n")

def main_crop(argv_list=None):
    """Process command-line arguments, do the PDF processing, and then perform final
    processing on the filenames.  If `argv_list` is set then it is used instead of
    `sys.argv`.  Returns the pathname of the output document."""
    parsed_args = parse_command_line_arguments(cmd_parser, argv_list=argv_list)

    # Process some of the command-line arguments (also sets `args` globally).
    input_doc_pathname, fixed_input_doc_pathname, output_doc_pathname = (
                                           process_command_line_arguments(parsed_args,
                                                                          cmd_parser))

    if args.gui:
        from .gui import create_gui # Import here; tkinter might not be installed.
        if args.verbose:
            print("\nWaiting for the GUI...")

        did_crop, bounding_box_list, delta_page_nums = create_gui(input_doc_pathname,
                              fixed_input_doc_pathname, output_doc_pathname,
                              cmd_parser, parsed_args)
        if did_crop:
            handle_options_on_cropped_file(input_doc_pathname, output_doc_pathname)
    else:
        bounding_box_list, delta_page_nums = process_pdf_file(input_doc_pathname,
                                                              fixed_input_doc_pathname,
                                                              output_doc_pathname)
        handle_options_on_cropped_file(input_doc_pathname, output_doc_pathname)

    return output_doc_pathname

