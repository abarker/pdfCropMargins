"""

This module contains the routines which calculate the bounding boxes,
either directly by rendering the pages and analyzing the image or by calling
Ghostscript to do it.  External programs from the external_program_calls
module are called when required.

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

from __future__ import print_function, division, absolute_import
import sys
import os
import glob
import time
from . import external_program_calls as ex
from . import pymupdf_routines

#
# Image-processing imports.
#

try:
    # The Pillow fork uses the same import command, so this import works either
    # way (but Pillow can't co-exist with PIL).
    from PIL import Image, ImageFilter, __version__ as pillow_version
    has_pillow = True
except ImportError:
    has_pillow = False

if has_pillow:
    pillow_version_tuple = tuple(int(i) for i in pillow_version.split("."))
    if pillow_version_tuple < (7,1,0):
        from warnings import warn
        w = ("Your installed pillow version {} is < 7.1.0. "
             "There are several moderate-severity security vulnerabilities "
             "in Pillow 6.2.2 which have since been fixed.  Python 2 support was "
             "dropped for Pillow versions after 7.0.0, however.  If you cannot upgrade to "
             "Python 3 it is recommended to use the '--calcbb gb' option to find bounding "
             "boxes.  (Unfortunately, that method does not work with scanned documents.)"
             .format(pillow_version))
        warn(w)

#
# A few globals used in this module, shared when passed into get_bounding_box_list.
#

args = None # Command-line arguments; set in get_bounding_box_list.

#
# The main functions of the module.
#

def get_bounding_box_list(input_doc_fname, input_doc, full_page_box_list,
                          set_of_page_nums_to_crop, argparse_args, chosen_PdfFileWriter):
    """Calculate a bounding box for each page in the document.  The
    `input_doc_fname` argument is the filename of the document's original PDF
    file, `input_doc` is the `PdfFileReader` for the document.  The argument
    `full_page_box_list` is a list of the full-page-size boxes (which is used
    to correct for any nonzero origins in the PDF coordinates).  The
    `set_of_page_nums_to_crop` argument is the set of page numbers to crop; it
    is passed so that unnecessary calculations can be skipped.  The
    `argparse_args` argument should be passed the args parsed from the command
    line by argparse.  The `chosen_PdfFileWriter` is the PdfFileWriter class
    from whichever pyPdf package was chosen by the main program.  The function
    returns the list of bounding boxes."""
    global args
    args = argparse_args # Make args available to all funs in module, as a global.

    if args.calcbb == "gb":
        if args.verbose:
            print("\nUsing Ghostscript to calculate the bounding boxes.")
        bbox_list = ex.get_bounding_box_list_ghostscript(input_doc_fname,
                                             args.resX, args.resY, args.fullPageBox)
    else:
        if not has_pillow:
            print("\nError in pdfCropMargins: No version of the Python 'pillow'"
                  "\npackage was found.  Either install that Python package or use"
                  "\nGhostscript directly ('--calcbb gb' or '--gsBbox') if you"
                  "\nhave Ghostscript installed.", file=sys.stderr)
            ex.cleanup_and_exit(1)

        bbox_list = get_bounding_box_list_render_image(input_doc_fname, input_doc)

    # Now we need to use the full page boxes to translate for non-zero origin.
    bbox_list = correct_bounding_box_list_for_nonzero_origin(bbox_list, full_page_box_list)

    return bbox_list

def correct_bounding_box_list_for_nonzero_origin(bbox_list, full_box_list):
    """The bounding box calculated from an image has coordinates relative to the
    lower-left point in the PDF being at zero.  Similarly, Ghostscript reports a
    bounding box relative to a zero lower-left point.  If the MediaBox (or full
    page box) has been shifted, like when cropping a previously cropped
    document, then we need to correct the bounding box by an additive
    translation on all the points."""

    corrected_box_list = []
    for bbox, full_box in zip(bbox_list, full_box_list):
        left_x = full_box[0]
        lower_y = full_box[1]
        corrected_box_list.append([bbox[0]+left_x, bbox[1]+lower_y,
                                 bbox[2]+left_x, bbox[3]+lower_y])
    return corrected_box_list

def get_bounding_box_list_render_image(pdf_file_name, input_doc):
    """Calculate the bounding box list by directly rendering each page of the PDF as
    an image file.  The MediaBox and CropBox values in `input_doc` should have
    already been set to the chosen page size before the rendering."""
    if args.calcbb == "m":
        program_to_use = "mupdf"
    elif args.calcbb == "p":
        program_to_use = "pdftoppm"
    elif args.calcbb == "gr":
        program_to_use = "Ghostscript"
    else:
        raise ValueError("Attempting render pages when no rendering method was specified"
                "\nPassed 'calcbb' argument of '{}'.".format(args.calcbb))

    if args.verbose:
        print("\nRendering the PDF to images using the " + program_to_use + " program,"
              "\nthis may take a while...")

    # Threshold value set in range 0-255, where 0 is black, with 191 default.
    threshold = args.threshold[0]
    dark_background_light_foreground = False
    if threshold < 0:
        threshold = -threshold
        dark_background_light_foreground = True

    if program_to_use == "mupdf":
        image_list = get_image_list_mupdf(pdf_file_name) # Images are PPM bytes objects.
        outfiles = [None] * len(image_list)

    else:
        temp_dir = ex.program_temp_directory
        temp_image_file_root = os.path.join(temp_dir, ex.temp_file_prefix + "PageImage")

        # Do the rendering of all the files.
        render_pdf_file_to_image_files(pdf_file_name, temp_image_file_root, program_to_use)

        # Currently assuming that sorting the output will always put them in correct order.
        outfiles = sorted(glob.glob(temp_image_file_root + "*"))

    if args.verbose:
        print("\nAnalyzing the page images with Pillow to find bounding boxes,"
              "\nusing the threshold " + str(args.threshold[0]) + "."
              "  Finding the bounding box for page:\n")

    bounding_box_list = []

    for page_num, tmp_image_file_name in enumerate(outfiles):
        curr_page = input_doc.getPage(page_num)

        # Open the image in Pillow.  Retry a few times on fail in case race conditions.
        if program_to_use == "mupdf":
            import io
            image = image_list[page_num]
            # Opening directly in Pillow: https://github.com/pymupdf/PyMuPDF/issues/322
            pil_im = Image.open(io.BytesIO(image))

        else:
            max_num_tries = 3
            time_between_tries = 1
            curr_num_tries = 0
            while True:
                try:
                    # PIL for some reason fails in Python 3.4 if you open the image
                    # from a file you opened yourself.  Works in Python 2 and earlier
                    # Python 3.  So original code is commented out, and path passed.
                    #
                    # tmpImageFile = open(tmpImageFileName)
                    # im = Image.open(tmpImageFile)
                    pil_im = Image.open(tmp_image_file_name)
                    break
                except (IOError, UnicodeDecodeError) as e:
                    curr_num_tries += 1
                    if args.verbose:
                        print("Warning: Exception opening image", tmp_image_file_name,
                              "on try", curr_num_tries, "\nError is", e, file=sys.stderr)
                    # tmpImageFile.close() # see above comment
                    if curr_num_tries > max_num_tries:
                        raise
                    time.sleep(time_between_tries)

        # Apply any blur or smooth operations specified by the user.
        for i in range(args.numBlurs):
            pil_im = pil_im.filter(ImageFilter.BLUR)
        for i in range(args.numSmooths):
            pil_im = pil_im.filter(ImageFilter.SMOOTH_MORE)

        # Convert the image to black and white, according to a threshold.
        # Make a negative image, because that works with the Pillow getbbox routine.

        if args.verbose:
            print(page_num+1, end=" ") # page num numbering from 1
        # Note that the point method calls the function on each pixel, replacing it.
        #im = im.point(lambda p: p > threshold and 255) # create a positive image
        #im = im.point(lambda p: p < threshold and 255)  # create a negative image
        # Below code is easier to understand than the tricky use of "and" in evaluation.
        if not dark_background_light_foreground:
            pil_im = pil_im.point(lambda p: 255 if p < threshold else 0) # create negative image
        else:
            pil_im = pil_im.point(lambda p: 255 if p >= threshold else 0) # create positive image

        if args.showImages:
            pil_im.show() # usually for debugging or param-setting

        # Calculate the bounding box of the negative image, and append to list.
        bounding_box = calculate_bounding_box_from_image(pil_im, curr_page)
        bounding_box_list.append(bounding_box)

        # Clean up the image files after they are no longer needed.
        # tmpImageFile.close() # see above comment
        if tmp_image_file_name:
            os.remove(tmp_image_file_name)

    if args.verbose:
        print()
    return bounding_box_list

def render_pdf_file_to_image_files(pdf_file_name, output_filename_root, program_to_use):
    """Render all the pages of the PDF file at pdf_file_name to image files with
    path and filename prefix given by output_filename_root.  Any directories must
    have already been created, and the calling program is responsible for
    deleting any directories or image files.  The program program_to_use,
    currently either the string "pdftoppm" or the string "Ghostscript", will be
    called externally.  The image type that the PDF is converted into must to be
    directly openable by Pillow."""

    res_x = str(args.resX)
    res_y = str(args.resY)

    if program_to_use == "Ghostscript":
        if ex.system_os == "Windows": # Windows PIL is more likely to know BMP
            ex.render_pdf_file_to_image_files_ghostscript_bmp(
                                  pdf_file_name, output_filename_root, res_x, res_y)
        else: # Linux and Cygwin should be fine with PNG
            ex.render_pdf_file_to_image_files_ghostscript_png(
                                  pdf_file_name, output_filename_root, res_x, res_y)

    elif program_to_use == "pdftoppm":
        use_gray = False # This is currently hardcoded, but can be changed to use pgm.
        if use_gray:
            ex.render_pdf_file_to_image_files_pdftoppm_pgm(
                pdf_file_name, output_filename_root, res_x, res_y)
        else:
            ex.render_pdf_file_to_image_files_pdftoppm_ppm(
                pdf_file_name, output_filename_root, res_x, res_y)

    else:
        print("Error in renderPdfFileToImageFile: Unrecognized external program.",
              file=sys.stderr)
        ex.cleanup_and_exit(1)

def get_image_list_mupdf(pdf_file_name):
    """Get the bounding boxes by rendering the pages with PyMuPDF and calculating
    them."""
    document_pages = pymupdf_routines.MuPdfDocument(args)
    num_pages = document_pages.open_document(pdf_file_name)

    # Note that the images here are PPM bytes objects.
    page_images = [document_pages.get_page_ppm_for_crop(i) for i in range(num_pages)]
    return page_images

def calculate_bounding_box_from_image(im, curr_page):
    """This function uses a Pillow routine to get the bounding box, in bp, of
    the rendered image."""
    x_max, y_max = im.size
    bounding_box = im.getbbox() # Note this uses ltrb convention.
    if not bounding_box:
        #print("\nWarning: could not calculate a bounding box for this page."
        #      "\nAn empty page is assumed.", file=sys.stderr)
        bounding_box = (x_max/2, y_max/2, x_max/2, y_max/2)

    bounding_box = list(bounding_box) # Make temporarily mutable.

    # Compensate for reversal of the image y convention versus PDF.
    bounding_box[1] = y_max - bounding_box[1]
    bounding_box[3] = y_max - bounding_box[3]

    full_page_box = curr_page.mediaBox # Should have been set already to chosen box.

    # Convert pixel units to PDF's bp units.
    convert_x = float(full_page_box.getUpperRight_x()
                    - full_page_box.getLowerLeft_x()) / x_max
    convert_y = float(full_page_box.getUpperRight_y()
                    - full_page_box.getLowerLeft_y()) / y_max

    # Get final box; note conversion to lower-left point, upper-right point format.
    final_box = [bounding_box[0] * convert_x,
                 bounding_box[3] * convert_y,
                 bounding_box[2] * convert_x,
                 bounding_box[1] * convert_y]

    return final_box

