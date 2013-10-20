"""

This module contains the routines which calculate the bounding boxes,
either directly by rendering the pages and analyzing the image or by calling
Ghostscript to do it.  External programs from the external_program_calls
module are called when required.

"""

from __future__ import print_function, division
import sys, os
import external_program_calls as ex

#
# Image-processing imports.
#

try:
   # Note that the Pillow fork uses the same import command,
   # so this import works either way (but Pillow can't co-exist with PIL).
   from PIL import Image, ImageFilter
   hasPIL = True
except ImportError:
   hasPIL = False

#
# A few globals used in this module.
#

args = None # Command-line arguments; initialized in getBoundingBoxList.
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
   class from whichever pyPdf package was chosen by the main program.  This
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
         sys.exit(1)
      bboxList = getBoundingBoxListRenderImage(inputDoc)
   
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


def getBoundingBoxListRenderImage(inputDoc):
   """Calculate the bounding box list by directly rendering each page of the PDF as
   an image file.  Note that the MediaBox and CropBox have already been set
   to the chosen page size before the rendering."""

   programToUse="pdftoppm" # default to pdftoppm
   if args.gsRender: programToUse="Ghostscript"
   # TODO: maybe add option to use other programs, from command-line or hardcoded

   # Threshold value set in range 0-255, where 0 is black, with 191 default.
   if not args.threshold: args.threshold = 191
   threshold = args.threshold
   if not args.numSmooths: args.numSmooths = 0
   if not args.numBlurs: args.numBlurs = 0

   if args.verbose:
      print("\nRendering PDF to images with the", programToUse,
            "program, using\nthe threshold " + str(args.threshold) +
            ".  Finding the bounding box for page:\n", end="")

   boundingBoxList = []

   # TODO get temp dir here and use progs to dump all pages in to it,
   # then cycle through them.  Do inside a try...except catching
   # KeyboardInterrupt and deleting the temp dir when that happens
   # (or think of a better way to do that).

   for page in range(inputDoc.getNumPages()):

      # Get the current page.
      currPage = inputDoc.getPage(page)

      # Set to MediaBox if not needed for this page; don't waste time rendering, etc.
      # Note this really isn't correct, but it won't be used and needs to be set to
      # some values.  (Should subtract off origin if really used, so correction fixes.)
      if page not in pageNumsToCrop:
         boundingBox = None
         boundingBox = [ float(currPage.mediaBox[i]) for i in range(4) ]
         boundingBoxList.append(boundingBox)
         continue
   
      # Create a temporary writer (to write the page as a PDF file).
      tmpOutputDoc = PdfFileWriter() # declare a tmp output
      tmpOutputDoc.addPage(currPage) # add current page to it

      # Make an output file and write the PDF to it.
      tmpPdfFileName = ex.getTemporaryFilename(".pdf")
      tmpPdfFileObject = open(tmpPdfFileName, "wb")
      tmpOutputDoc.write(tmpPdfFileObject)
      tmpPdfFileObject.close()
      
      # Render the PDF file to a temporary image file. 
      tmpImageFileName = renderPdfFileToImageFile(tmpPdfFileName, programToUse)

      # Open the image in PIL.
      im = Image.open(tmpImageFileName)

      # Apply any blur or smooth operations specified by the user.
      for i in range(args.numBlurs):
         im = im.filter(ImageFilter.BLUR)
      for i in range(args.numSmooths):
         im = im.filter(ImageFilter.SMOOTH_MORE)
   
      # Convert the image to black and white, according to a threshold.
      # Make a negative image, because that works with the PIL getbbox routine.

      if args.verbose: print(page+1, end=" ") # page num numbering from 1
      # Note: the point method calls the function on each pixel, replacing it.
      #im = im.point(lambda p: p > threshold and 255) # create a positive image
      im = im.point(lambda p: p < threshold and 255)  # create a negative image
      
      if args.showImages: im.show() # usually for debugging or param-setting
   
      # Calculate the bounding box of the negative image, and append to list.
      boundingBox = calculateBoundingBoxFromImage(im, currPage)
      boundingBoxList.append(boundingBox)

      # Clean up the temporary files for this iteration of the loop.
      os.remove(tmpPdfFileName)
      os.remove(tmpImageFileName)

   if args.verbose: print()
   return boundingBoxList

def renderPdfFileToImageFile(pdfFileName, programToUse):
   """Render the PDF file at pdfFileName to an image file in a temporary
   filename, at the given resolution.  The program programToUse, currently
   either the string "pdftoppm" or the string "Ghostscript", will be called
   externally.  The image type that the PDF is converted into must to be
   directly openable by PIL.  This function returns the temporary file's name.
   The calling program is responsible for deleting the file."""

   resX = str(args.resX)
   resY = str(args.resY)
   if programToUse == "Ghostscript":
      fileExtension = ".png"
      imageFileName = ex.getTemporaryFilename(fileExtension)
      ex.renderPdfFileToImageFile_Ghostscript_png(pdfFileName, imageFileName, resX, resY)
   elif programToUse == "pdftoppm":
      use_gray = False # this is currently hardcoded, but can be changed to use pgm
      if use_gray:
         fileExtension = ".pgm" # use graymap, not full color map
         imageFileName = ex.getTemporaryFilename(fileExtension)
         ex.renderPdfFileToImageFile_pdftoppm_pgm(pdfFileName, imageFileName, resX, resY)
      else:
         fileExtension = ".ppm"
         imageFileName = ex.getTemporaryFilename(fileExtension)
         ex.renderPdfFileToImageFile_pdftoppm_ppm(pdfFileName, imageFileName, resX, resY)
   else:
      print("Error in renderPdfFileToImageFile: Unrecognized external program.",
            file=sys.stderr)
      sys.exit(1)
   return imageFileName


def calculateBoundingBoxFromImage(im, currPage):
   """This function uses a PIL routine to get the bounding box of the rendered
   image."""
   xMax, yMax = im.size
   boundingBox = im.getbbox() # note this uses ltrb convention
   if not boundingBox:
      print("\nWarning: could not calculate a bounding box for this page."
            "\nAn empty page is assumed.", file=sys.stderr)
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
                  - fullPageBox.getLowerLeft_y() ) / yMax

   # Get final box; note conversion to lower-left point, upper-right point format.
   finalBox = [
         boundingBox[0] * convertX,
         boundingBox[3] * convertY,
         boundingBox[2] * convertX,
         boundingBox[1] * convertY]

   return finalBox

