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

This module contains the routines which calculate the bounding boxes,
either directly by rendering the pages and analyzing the image or by calling
Ghostscript to do it.  External programs from the external_program_calls
module are called when required.

"""

from __future__ import print_function, division
import sys
import os
import glob
import shutil
import time
from . import external_program_calls as ex

#
# Image-processing imports.
#

try:
    # The Pillow fork uses the same import command, so this import works either
    # way (but Pillow can't co-exist with PIL).
    from PIL import Image, ImageFilter
    hasPIL = True
except ImportError:
    hasPIL = False

#
# A few globals used in this module.
#

args = None # Command-line arguments; set in getBoundingBoxList.
pageNumsToCrop = None # Set of pages to crop; initialized in getBoundingBoxList.
PdfFileWriter = None # Initialized in getBoundingBoxList

#
# The main functions of the module.
#


def getBoundingBoxList(inputDocFname, inputDoc, fullPageBoxList,
                       setOfPageNumsToCrop, argparseArgs, ChosenPdfFileWriter):
    """Calculate a bounding box for each page in the document.  The first
    argument is the filename of the document's original PDF file, the second is
    the PdfFileReader for the document.  The argument fullPageBoxList is a list
    of the full-page-size boxes (which is used to correct for any nonzero origins
    in the PDF coordinates).  The setOfPageNumsToCrop argument is the set of page
    numbers to crop; it is passed so that unnecessary calculations can be
    skipped.  The argparseArgs argument should be passed the args parsed from
    the command line by argparse.  The ChosenPdfFileWriter is the PdfFileWriter
    class from whichever pyPdf package was chosen by the main program.  The
    function returns the list of bounding boxes."""
    global args, pageNumsToCrop, PdfFileWriter
    args = argparseArgs # Make args available to all funs in module, as a global.
    pageNumsToCrop = setOfPageNumsToCrop # Make the set of pages global, too.
    PdfFileWriter = ChosenPdfFileWriter # Be sure correct PdfFileWriter is set.

    if args.gsBbox:
        if args.verbose:
            print("\nUsing Ghostscript to calculate the bounding boxes.")
        bboxList = ex.getBoundingBoxListGhostscript(inputDocFname, args.resX, args.resY,
                                                    args.fullPageBox)
    else:
        if not hasPIL:
            print("\nError in pdfCropMargins: No version of the PIL package (or a"
                  "\nfork like Pillow) was found.  Either install that Python"
                  "\npackage or use the Ghostscript flag '--gsBbox' (or '-gs') if you"
                  "\nhave Ghostscript installed.", file=sys.stderr)
            ex.cleanupAndExit(1)
        bboxList = getBoundingBoxListRenderImage(inputDocFname, inputDoc)

    # Now we need to use the full page boxes to translate for non-zero origin.
    bboxList = correctBoundingBoxListForNonzeroOrigin(bboxList, fullPageBoxList)

    return bboxList


def correctBoundingBoxListForNonzeroOrigin(bboxList, fullBoxList):
    """The bounding box calculated from an image has coordinates relative to the
    lower-left point in the PDF being at zero.  Similarly, Ghostscript reports a
    bounding box relative to a zero lower-left point.  If the MediaBox (or full
    page box) has been shifted, like when cropping a previously cropped
    document, then we need to correct the bounding box by an additive
    translation on all the points."""

    correctedBoxList = []
    for bbox, fullBox in zip(bboxList, fullBoxList):
        leftX = fullBox[0]
        lowerY = fullBox[1]
        correctedBoxList.append([bbox[0]+leftX, bbox[1]+lowerY,
                                 bbox[2]+leftX, bbox[3]+lowerY])
    return correctedBoxList


def getBoundingBoxListRenderImage(pdfFileName, inputDoc):
    """Calculate the bounding box list by directly rendering each page of the PDF as
    an image file.  The MediaBox and CropBox values in inputDoc should have
    already been set to the chosen page size before the rendering."""

    programToUse = "pdftoppm" # default to pdftoppm
    if args.gsRender: programToUse = "Ghostscript"

    # Threshold value set in range 0-255, where 0 is black, with 191 default.
    if not args.threshold: args.threshold = 191
    threshold = args.threshold
    if not args.numSmooths: args.numSmooths = 0
    if not args.numBlurs: args.numBlurs = 0

    tempDir = ex.programTempDirectory # use the program default; don't delete dir!

    tempImageFileRoot = os.path.join(tempDir, ex.tempFilePrefix + "PageImage")
    if args.verbose:
        print("\nRendering the PDF to images using the " + programToUse + " program,"
              "\nthis may take a while...")

    # Do the rendering of all the files.
    renderPdfFileToImageFiles(pdfFileName, tempImageFileRoot, programToUse)

    # Currently assuming that sorting the output will always put them in correct order.
    outfiles = sorted(glob.glob(tempImageFileRoot + "*"))

    if args.verbose:
        print("\nAnalyzing the page images with PIL to find bounding boxes,"
              "\nusing the threshold " + str(args.threshold) + "."
              "  Finding the bounding box for page:\n")

    boundingBoxList = []

    for pageNum, tmpImageFileName in enumerate(outfiles):
        currPage = inputDoc.getPage(pageNum)

        # Open the image in PIL.  Retry a few times on fail in case race conditions.
        maxNumTries = 3
        timeBetweenTries = 1
        currNumTries = 0
        while True:
            try:
                # PIL for some reason fails in Python 3.4 if you open the image
                # from a file you opened yourself.  Works in Python 2 and earlier
                # Python 3.  So original code is commented out, and path passed.
                #
                # tmpImageFile = open(tmpImageFileName)
                # im = Image.open(tmpImageFile)
                im = Image.open(tmpImageFileName)
                break
            except (IOError, UnicodeDecodeError) as e:
                currNumTries += 1
                if args.verbose:
                    print("Warning: Exception opening image", tmpImageFileName,
                          "on try", currNumTries, "\nError is", e, file=sys.stderr)
                # tmpImageFile.close() # see above comment
                if currNumTries > maxNumTries: raise # re-raise exception
                time.sleep(timeBetweenTries)

        # Apply any blur or smooth operations specified by the user.
        for i in range(args.numBlurs):
            im = im.filter(ImageFilter.BLUR)
        for i in range(args.numSmooths):
            im = im.filter(ImageFilter.SMOOTH_MORE)

        # Convert the image to black and white, according to a threshold.
        # Make a negative image, because that works with the PIL getbbox routine.

        if args.verbose: print(pageNum+1, end=" ") # page num numbering from 1
        # Note: the point method calls the function on each pixel, replacing it.
        #im = im.point(lambda p: p > threshold and 255) # create a positive image
        im = im.point(lambda p: p < threshold and 255)  # create a negative image

        if args.showImages: im.show() # usually for debugging or param-setting

        # Calculate the bounding box of the negative image, and append to list.
        boundingBox = calculateBoundingBoxFromImage(im, currPage)
        boundingBoxList.append(boundingBox)

        # Clean up the image files after they are no longer needed.
        # tmpImageFile.close() # see above comment
        os.remove(tmpImageFileName)

    if args.verbose: print()
    return boundingBoxList


def renderPdfFileToImageFiles(pdfFileName, outputFilenameRoot, programToUse):
    """Render all the pages of the PDF file at pdfFileName to image files with
    path and filename prefix given by outputFilenameRoot.  Any directories must
    have already been created, and the calling program is responsible for
    deleting any directories or image files.  The program programToUse,
    currently either the string "pdftoppm" or the string "Ghostscript", will be
    called externally.  The image type that the PDF is converted into must to be
    directly openable by PIL."""

    resX = str(args.resX)
    resY = str(args.resY)
    if programToUse == "Ghostscript":
        if ex.systemOs == "Windows": # Windows PIL is more likely to know BMP
            ex.renderPdfFileToImageFiles_Ghostscript_bmp(
                                  pdfFileName, outputFilenameRoot, resX, resY)
        else: # Linux and Cygwin should be fine with PNG
            ex.renderPdfFileToImageFiles_Ghostscript_png(
                                  pdfFileName, outputFilenameRoot, resX, resY)
    elif programToUse == "pdftoppm":
        use_gray = False # this is currently hardcoded, but can be changed to use pgm
        if use_gray:
            ex.renderPdfFileToImageFiles_pdftoppm_pgm(
                pdfFileName, outputFilenameRoot, resX, resY)
        else:
            ex.renderPdfFileToImageFiles_pdftoppm_ppm(
                pdfFileName, outputFilenameRoot, resX, resY)
    else:
        print("Error in renderPdfFileToImageFile: Unrecognized external program.",
              file=sys.stderr)
        ex.cleanupAndExit(1)
    return


def calculateBoundingBoxFromImage(im, currPage):
    """This function uses a PIL routine to get the bounding box of the rendered
    image."""
    xMax, yMax = im.size
    boundingBox = im.getbbox() # note this uses ltrb convention
    if not boundingBox:
        #print("\nWarning: could not calculate a bounding box for this page."
        #      "\nAn empty page is assumed.", file=sys.stderr)
        boundingBox = (xMax/2, yMax/2, xMax/2, yMax/2)

    boundingBox = list(boundingBox) # make temporarily mutable

    # Compensate for reversal of the image y convention versus PDF.
    boundingBox[1] = yMax - boundingBox[1]
    boundingBox[3] = yMax - boundingBox[3]

    fullPageBox = currPage.mediaBox # should have been set already to chosen box

    # Convert pixel units to PDF's bp units.
    convertX = float(fullPageBox.getUpperRight_x()
                     - fullPageBox.getLowerLeft_x()) / xMax
    convertY = float(fullPageBox.getUpperRight_y()
                     - fullPageBox.getLowerLeft_y()) / yMax

    # Get final box; note conversion to lower-left point, upper-right point format.
    finalBox = [
        boundingBox[0] * convertX,
        boundingBox[3] * convertY,
        boundingBox[2] * convertX,
        boundingBox[1] * convertY]

    return finalBox
