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

from __future__ import print_function, division
import sys
import os
import shutil
import time

##
## Import the module that calls external programs and gets system info.
##

from . import external_program_calls as ex
pythonVersion = ex.pythonVersion
projectSrcDirectory = ex.projectSrcDirectory

##
## Try to import the system pyPdf.  If that fails or if the '--pyPdfLocal'
## option was set then revert to the appropriate local version.
##

pyPdfLocal = False # TODO delete cleanup
# Peek at the command line (before fully parsing it later) to see if we should
# import the local pyPdf.  This works for simple options which are either set
# or not.  Note that importing is now dependent on sys.argv (even though it
# shouldn't make a difference in this application).
if "--pyPdfLocal" in sys.argv or "-pdl" in sys.argv:
    #pyPdfLocal = True
    pyPdfLocal = False # NEVER USE LOCAL

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

from .calculate_bounding_boxes import getBoundingBoxList

##
## Import the prettified argparse module and the text of the manpage documentation.
##

from .prettified_argparse import parseCommandLineArguments
from .manpage_data import cmdParser

##
## Some general strings used by the program.
##

# The string which is appended to Producer metadata in cropped PDFs.
producerModifier = " (Cropped by pdfCropMargins.)"


##
## Begin general function definitions.
##


def generateDefaultFilename(infilePath, isCroppedFile=True):
    """Generate the name of the default output file from the name of the input
    file.  The isCroppedFile boolean is used to indicate that the file has been
    (or will be) cropped, to determine which filename-modification string to
    use.  Function assumes that args has been set globally by argparse."""

    if isCroppedFile: suffix = prefix = args.stringCropped
    else: suffix = prefix = args.stringUncropped

    # Use modified basename as output path; program writes default output to CWD.
    fileName = os.path.basename(infilePath)
    nameBeforeExtension, extension = os.path.splitext(fileName)
    if extension not in {".pdf", ".PDF"}: extension += ".pdf"

    sep = args.stringSeparator
    if args.usePrefix: name = prefix + sep + nameBeforeExtension + extension
    else: name = nameBeforeExtension + sep + suffix + extension

    return name


def intersectBoxes(box1, box2):
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


def modBoxForRotation(box, angle, undo=False):
    """The user sees left, bottom, right, and top margins on a page, but inside
    the PDF and in pyPdf the page may be rotated (such as in landscape mode).
    In the case of 90 degree clockwise rotation the left really modifies the
    top, the top really modifies right, and so forth.  In order for the options
    like '--percentRetain4' and '--absoluteOffset4' to work as expected the
    values need to be shifted to match any "hidden" rotations on any page."""

    def rotateNinetyDegreesClockwise(box, n):
        if n == 0: return box
        box = rotateNinetyDegreesClockwise(box, n-1)
        return [box[1], box[2], box[3], box[0]]

    # These are for clockwise, swap do and undo to reverse.
    doMap = {0: 0, 90: 1, 180: 2, 270: 3}
    undoMap = {0: 0, 90: 3, 180: 2, 270: 1}

    if not undo:
        return rotateNinetyDegreesClockwise(box, doMap[angle])
    else:
        return rotateNinetyDegreesClockwise(box, undoMap[angle])
    return


def getFullPageBoxAssigningMediaAndCrop(page):
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

    firstLoop = True
    for boxString in args.fullPageBox:
        if boxString == "m": fBox = page.mediaBox
        if boxString == "c": fBox = page.cropBox
        if boxString == "t": fBox = page.trimBox
        if boxString == "a": fBox = page.artBox
        if boxString == "b": fBox = page.bleedBox

        # Take intersection over all chosen boxes.
        if firstLoop:
            fullBox = fBox
        else:
            fullBox = intersectBoxes(fullBox, fBox)

        firstLoop = False

    # Do any absolute pre-cropping specified for the page (after modifying any
    # absolutePreCrop arguments to take into account rotations to the page).
    a = modBoxForRotation(args.absolutePreCrop, rotation)
    fullBox = RectangleObject([float(fullBox.lowerLeft[0]) + a[0],
                               float(fullBox.lowerLeft[1]) + a[1],
                               float(fullBox.upperRight[0]) - a[2],
                               float(fullBox.upperRight[1]) - a[3]])

    page.mediaBox = fullBox
    page.cropBox = fullBox

    return fullBox


def getFullPageBoxListAssigningMediaAndCrop(inputDoc, quiet=False):
    """Get a list of all the full-page box values for each page.  The argument
    inputDoc should be a PdfFileReader object.  The boxes on the list are in the
    simple 4-float list format used by this program, not RectangleObject format."""

    fullPageBoxList = []
    rotationList = []

    if args.verbose and not quiet:
        print("\nOriginal full page sizes, in PDF format (lbrt):")

    for pageNum in range(inputDoc.getNumPages()):

        # Get the current page and find the full-page box.
        currPage = inputDoc.getPage(pageNum)
        fullPageBox = getFullPageBoxAssigningMediaAndCrop(currPage)

        if args.verbose and not quiet:
            # want to display page num numbering from 1, so add one
            print("\t"+str(pageNum+1), "  rot =",
                  currPage.rotationAngle, "\t", fullPageBox)

        # Convert the RectangleObject to floats in an ordinary list and append.
        ordinaryBox = [float(b) for b in fullPageBox]
        fullPageBoxList.append(ordinaryBox)

        # Append the rotation value to the rotationList.
        rotationList.append(currPage.rotationAngle)

    return fullPageBoxList, rotationList


def calculateCropList(fullPageBoxList, boundingBoxList, angleList, pageNumsToCrop):
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

    numPages = len(boundingBoxList)
    pageRange = range(numPages)
    numPagesToCrop = len(pageNumsToCrop)

    # Handle the '--samePageSize' option.
    # Note that this is always done first, over the whole document, even before
    # pages and evenodd are handled.
    if args.samePageSize:
        if args.verbose:
            print("\nSetting each page size to the smallest box bounding all the pages.")
        fullPageBoxList = [[min(box[0] for box in fullPageBoxList),
                            min(box[1] for box in fullPageBoxList),
                            max(box[2] for box in fullPageBoxList),
                            max(box[3] for box in fullPageBoxList)]
                           ] * numPages

    # Handle the '--evenodd' option if it was selected.
    if args.evenodd:
        evenPageNumsToCrop = {pNum for pNum in pageNumsToCrop if pNum % 2 == 0}
        oddPageNumsToCrop = {pNum for pNum in pageNumsToCrop if pNum % 2 != 0}

        if args.uniform: uniformSetWithEvenOdd = True
        else: uniformSetWithEvenOdd = False

        # Recurse on even and odd pages, after resetting some options.
        if args.verbose: print("\nRecursively calculating crops for even and odd pages.")
        args.evenodd = False # avoid infinite recursion
        args.uniform = True  # --evenodd implies uniform, just on each separate group
        evenCropList = calculateCropList(
                       fullPageBoxList, boundingBoxList, angleList, evenPageNumsToCrop)
        oddCropList = calculateCropList(
                       fullPageBoxList, boundingBoxList, angleList, oddPageNumsToCrop)

        # Recombine the even and odd pages
        combineEvenOdd = []
        for pNum in pageRange:
            if pNum % 2 == 0: combineEvenOdd.append(evenCropList[pNum])
            else: combineEvenOdd.append(oddCropList[pNum])

        # Handle the case where --uniform was set with --evenodd
        if uniformSetWithEvenOdd:
            minBottomMargin = min([box[1] for box in combineEvenOdd])
            maxTopMargin = max([box[3] for box in combineEvenOdd])
            combineEvenOdd = [[box[0], minBottomMargin, box[2], maxTopMargin]
                              for box in combineEvenOdd]
        return combineEvenOdd

    # Before calculating the crops we modify the percentRetain and
    # absoluteOffset values for all the pages according to any specified
    # rotations for the pages.  This is so, for example, uniform cropping is
    # relative to what the user actually sees.
    rotatedPercentRetain = [modBoxForRotation(args.percentRetain, angleList[i])
                                                         for i in range(numPages)]
    rotatedAbsoluteOffset = [modBoxForRotation(args.absoluteOffset, angleList[i])
                                                         for i in range(numPages)]

    # Calculate the list of deltas to be used to modify the original page
    # sizes.  Basically, a delta is the absolute diff between the full and
    # tight-bounding boxes, scaled according to the user's percentRetain, with
    # any absolute offset then added (lb) or subtracted (tr) as appropriate.
    #
    # The deltas are all positive unless absoluteOffset changes that or
    # percent>100.  They are added (lb) or subtracted (tr) as appropriate.


    deltaList = []
    for pNum, tBox, fBox in zip(list(range(len(fullPageBoxList))),
                                               boundingBoxList, fullPageBoxList):
        deltas = [abs(tBox[i] - fBox[i]) for i in range(4)]
        adjDeltas = [deltas[i] * (100.0-rotatedPercentRetain[pNum][i]) / 100.0
                     for i in range(4)]
        adjDeltas = [adjDeltas[i] + rotatedAbsoluteOffset[pNum][i] for i in range(4)]
        deltaList.append(adjDeltas)

    # Handle the '--uniform' options if one was selected.
    if args.uniformOrderPercent:
        percentVal = args.uniformOrderPercent[0]
        if percentVal < 0.0: percentVal = 0.0
        if percentVal > 100.0: percentVal = 100.0
        args.uniformOrderStat = [int(round(numPagesToCrop * percentVal / 100.0))]

    if args.uniform or args.uniformOrderStat:
        if args.verbose: print("\nAll the selected pages will be uniformly cropped.")
        # Only look at the deltas which correspond to pages selected for cropping.
        # They will then be sorted for each margin and selected.
        cropDeltaList = [deltaList[j] for j in pageRange if j in pageNumsToCrop]

        i = 0 # Let i be the index value into the sorted delta list.
        if args.uniformOrderStat: i = args.uniformOrderStat[0]
        if i < 0 or i >= numPagesToCrop:
            print("\nWarning: The selected order statistic is out of range.",
                  "Setting to closest value.", file=sys.stderr)
            if i >= numPagesToCrop: i = numPagesToCrop - 1
            if i < 0: i = 0
        if args.verbose and (args.uniformOrderStat or args.uniformOrderPercent):
            print("\nThe " + str(i) +
                  " smallest delta values over the selected pages will be ignored"
                  "\nwhen choosing a common, uniform delta value for each margin.")
        leftVals = sorted([box[0] for box in cropDeltaList])
        lowerVals = sorted([box[1] for box in cropDeltaList])
        rightVals = sorted([box[2] for box in cropDeltaList])
        upperVals = sorted([box[3] for box in cropDeltaList])
        deltaList = [[leftVals[i], lowerVals[i], rightVals[i], upperVals[i]]] * numPages

    # Apply the delta modifications to the full boxes to get the final sizes.
    finalCropList = []
    for fBox, deltas in zip(fullPageBoxList, deltaList):
        finalCropList.append((fBox[0] + deltas[0], fBox[1] + deltas[1],
                              fBox[2] - deltas[2], fBox[3] - deltas[3]))

    return finalCropList


def setCroppedMetadata(inputDoc, outputDoc, inputMetadataInfo):
    """Set the metadata for the output document.  Mostly just copied over, but
    "Producer" has a string appended to indicate that this program modified the
    file.  That allows for the undo operation to make sure that this
    program cropped the file in the first place."""

    # Setting metadata with pyPdf requires low-level pyPdf operations, see
    # http://stackoverflow.com/questions/2574676/change-metadata-of-pdf-file-with-pypdf
    if not inputMetadataInfo: # In case it's null, just set values to empty strings.
        class inputMetadataInfo(object):
            pass
        inputMetadataInfo.author = ""
        inputMetadataInfo.creator = ""
        inputMetadataInfo.producer = ""
        inputMetadataInfo.subject = ""
        inputMetadataInfo.title = ""

    outputInfoDict = outputDoc._info.getObject()

    # Check Producer metadata attribute to see if this program cropped document before.
    global producerModifier
    alreadyCroppedByThisProgram = False
    oldProducerString = inputMetadataInfo.producer
    if oldProducerString and oldProducerString.endswith(producerModifier):
        if args.verbose:
            print("\nThe document was already cropped at least once by this program.")
        alreadyCroppedByThisProgram = True
        producerModifier = "" # No need to pile up suffixes each time on Producer.

    # Note that all None metadata attributes are currently set to the empty string
    # when passing along the metadata information.
    def st(item):
        if item is None: return ""
        else: return item

    outputInfoDict.update({
          NameObject("/Author"): createStringObject(st(inputMetadataInfo.author)),
          NameObject("/Creator"): createStringObject(st(inputMetadataInfo.creator)),
          NameObject("/Producer"): createStringObject(st(inputMetadataInfo.producer)
                                                                 + producerModifier),
          NameObject("/Subject"): createStringObject(st(inputMetadataInfo.subject)),
          NameObject("/Title"): createStringObject(st(inputMetadataInfo.title))
          })

    return alreadyCroppedByThisProgram


def applyCropList(cropList, inputDoc, pageNumsToCrop, alreadyCroppedByThisProgram):
    """Apply the crop list to the pages of the input PdfFileReader object."""

    if args.restore and not alreadyCroppedByThisProgram:
        print("\nWarning from pdfCropMargins: The Producer string indicates that"
              "\neither this document was not previously cropped by pdfCropMargins"
              "\nor else it was modified by another program after that.  Trying the"
              "\nundo anyway...", file=sys.stderr)

    if args.restore and args.verbose:
        print("\nRestoring the document to margins saved for each page in the ArtBox.")

    if args.verbose and not args.restore:
        print("\nNew full page sizes after cropping, in PDF format (lbrt):")

    # Copy over each page, after modifying the appropriate PDF boxes.
    for pageNum in range(inputDoc.getNumPages()):

        currPage = inputDoc.getPage(pageNum)

        # Restore any rotation which was originally on the page.
        currPage.rotateClockwise(currPage.rotationAngle)

        # Only do the restore from ArtBox if '--restore' option was selected.
        if args.restore:
            if not currPage.artBox:
                print("\nWarning from pdfCropMargins: Attempting to restore pages from"
                      "\nthe ArtBox in each page, but page", pageNum, "has no readable"
                      "\nArtBox.  Leaving that page unchanged.", file=sys.stderr)
                continue
            currPage.mediaBox = currPage.artBox
            currPage.cropBox = currPage.artBox
            continue

        # Do the save to ArtBox if that option is chosen and Producer is set.
        if not args.noundosave and not alreadyCroppedByThisProgram:
            currPage.artBox = intersectBoxes(currPage.mediaBox, currPage.cropBox)

        # Reset the CropBox and MediaBox to their saved original values
        # (which were set in getFullPageBox, in the currPage object's namespace).
        currPage.mediaBox = currPage.originalMediaBox
        currPage.cropBox = currPage.originalCropBox

        # Copy the original page without further mods if it wasn't in the range
        # selected for cropping.
        if pageNum not in pageNumsToCrop:
            continue

        # Convert the computed "box to crop to" into a RectangleObject (for pyPdf).
        newCroppedBox = RectangleObject(cropList[pageNum])

        if args.verbose:
            print("\t"+str(pageNum+1)+"\t", newCroppedBox) # page numbering from 1

        if not args.boxesToSet: args.boxesToSet = ["m", "c"]

        # Now set any boxes which were selected to be set via the --boxesToSet option.
        if "m" in args.boxesToSet: currPage.mediaBox = newCroppedBox
        if "c" in args.boxesToSet: currPage.cropBox = newCroppedBox
        if "t" in args.boxesToSet: currPage.trimBox = newCroppedBox
        if "a" in args.boxesToSet: currPage.artBox = newCroppedBox
        if "b" in args.boxesToSet: currPage.bleedBox = newCroppedBox

    return


##############################################################################
#
# Begin the main script.
#
##############################################################################


# Parse the command-line arguments and set the variable args.
args = parseCommandLineArguments(cmdParser)

def mainCrop():
    """This function does the real work.  It is called by main() in
    pdfCropMargins.py, which just handles catching exceptions and cleaning up."""

    ##
    ## Process some of the command-line arguments.
    ##

    if args.verbose:
        print("\nProcessing the PDF with pdfCropMargins...\nSystem type:",
              ex.systemOs)

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

    inputDocFname = ex.globIfWindowsOs(args.pdf_input_doc, exactNumArgs=1)[0]
    if not inputDocFname.endswith((".pdf",".PDF")):
        print("\nWarning in pdfCropMargins: The file extension is neither '.pdf'"
              "\nnor '.PDF'; continuing anyway.\n", file=sys.stderr)
    if args.verbose:
        print("\nThe input document's filename is:\n   ", inputDocFname)
    if not os.path.isfile(inputDocFname):
        print("\nError in pdfCropMargins: The specified input file\n   "
              + inputDocFname + "\nis not a file or does not exist.",
              file=sys.stderr)
        ex.cleanupAndExit(1)

    if not args.outfile:
        if args.verbose: print("\nUsing the default-generated output filename.")
        outputDocFname = generateDefaultFilename(inputDocFname)
    else:
        outputDocFname = ex.globIfWindowsOs(args.outfile[0], exactNumArgs=1)[0]
    if args.verbose:
        print("\nThe output document's filename will be:\n   ", outputDocFname)

    if os.path.lexists(outputDocFname) and args.noclobber:
        print("\nOption '--noclobber' is set, refusing to overwrite an existing"
              "\nfile with filename:\n   ", outputDocFname, file=sys.stderr)
        ex.cleanupAndExit(1)

    if os.path.lexists(outputDocFname) and ex.samefile(inputDocFname,
                                                                outputDocFname):
        print("\nError in pdfCropMargins: The input file is the same as"
              "\nthe output file.\n", file=sys.stderr)
        ex.cleanupAndExit(1)

    if args.pdftoppmPath: ex.setPdftoppmExecutableToString(args.pdftoppmPath)
    if args.ghostscriptPath: ex.setGsExecutableToString(args.ghostscriptPath)

    # If the option settings require pdftoppm, make sure we have a running
    # version.  If '--gsBbox' isn't chosen then assume that PDF pages are to be
    # explicitly rendered.  In that case we either need pdftoppm or gs to do the
    # rendering.
    gsRenderFallbackSet = False # Set True if we switch to gs option as a fallback.
    if not args.gsBbox and not args.gsRender:
        foundPdftoppm = ex.initAndTestPdftoppmExecutable(preferLocal=args.pdftoppmLocal)
        if args.verbose: print("\nFound pdftoppm program at:", foundPdftoppm)
        if not foundPdftoppm:
            args.gsRender = True
            gsRenderFallbackSet = True
            if args.verbose:
                print("\nNo pdftoppm executable found; using Ghostscript for rendering.")

    # If any options require Ghostscript, make sure it it installed.
    if args.gsBbox or args.gsFix or args.gsRender:
        foundGs = ex.initAndTestGsExecutable()
        if args.verbose: print("\nFound Ghostscript program at:", foundGs)
    if args.gsBbox and not foundGs:
        print("\nError in pdfCropMargins: The '--gsBbox' option was specified but"
              "\nthe Ghostscript executable could not be located.  Is it"
              "\ninstalled and in the PATH for command execution?\n", file=sys.stderr)
        ex.cleanupAndExit(1)
    if args.gsFix and not foundGs:
        print("\nError in pdfCropMargins: The '--gsFix' option was specified but"
              "\nthe Ghostscript executable could not be located.  Is it"
              "\ninstalled and in the PATH for command execution?\n", file=sys.stderr)
        ex.cleanupAndExit(1)
    if args.gsRender and not foundGs:
        if gsRenderFallbackSet:
            print("\nError in pdfCropMargins: Neither Ghostscript nor pdftoppm"
                  "\nwas found in the PATH for command execution.  At least one is"
                  "\nrequired.\n", file=sys.stderr)
        else:
            print("\nError in pdfCropMargins: The '--gsRender' option was specified but"
                  "\nthe Ghostscript executable could not be located.  Is it"
                  "\ninstalled and in the PATH for command execution?\n", file=sys.stderr)
        ex.cleanupAndExit(1)

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
        fixedInputDocFname = ex.fixPdfWithGhostscriptToTmpFile(inputDocFname)
    else:
        fixedInputDocFname = inputDocFname

    fixedInputDocFileObject = open(fixedInputDocFname, "rb")
    try:
        inputDoc = PdfFileReader(fixedInputDocFileObject)
        tmpInputDoc = PdfFileReader(fixedInputDocFileObject)
    #except PdfReadError, ValueError: # throws various errors, just use general except
    except:
        print("\nError in pdfCropMargins: The pyPdf module failed in an attempt"
              "\nto read the input file.  Is the file a PDF file?  If so then it"
              "\nmay be corrupted.  If you have Ghostscript, try the '--gsFix'"
              "\noption (assuming you are not using it already).  That option can"
              "\nalso convert some PostScript files to a readable format.",
              file=sys.stderr)
        ex.cleanupAndExit(1)

    ##
    ## See if the document needs to be decrypted.
    ##

    if args.password:
        try:
            inputDoc.decrypt(args.password)
            tmpInputDoc.decrypt(args.password)
        except KeyError:
            print("\nDecrypting with the password from the '--password' option"
                  "\nfailed.", file=sys.stderr)
            ex.cleanupAndExit(1)
    else: # try decrypting with an empty password
        try:
            inputDoc.decrypt("")
            tmpInputDoc.decrypt("")
        except KeyError:
            pass # document apparently wasn't encrypted with an empty password

    ##
    ## Print out some data and metadata in verbose mode.
    ##

    if args.verbose:
        print("\nThe input document has %s pages." % inputDoc.getNumPages())

    try: # This is needed because the call sometimes just raises an error.
        metadataInfo = inputDoc.getDocumentInfo()
    except:
        metadataInfo = None

    if args.verbose and not metadataInfo:
        print("\nNo readable metadata in the document.")
    elif args.verbose:
        print("\nThe document's metadata, if set:\n")
        print("   The Author attribute set in the input document is:\n      %s"
              % (metadataInfo.author))
        print("   The Creator attribute set in the input document is:\n      %s"
              % (metadataInfo.creator))
        print("   The Producer attribute set in the input document is:\n      %s"
              % (metadataInfo.producer))
        print("   The Subject attribute set in the input document is:\n      %s"
              % (metadataInfo.subject))
        print("   The Title attribute set in the input document is:\n      %s"
              % (metadataInfo.title))

    ##
    ## Now compute the set containing the pyPdf page number of all the pages
    ## which the user has selected for cropping from the command line.  Most
    ## calculations are still carried-out for all the pages in the document.
    ## (There are a few optimizations for expensive operations like finding
    ## bounding boxes; the rest is negligible).  This keeps the correspondence
    ## between page numbers and the positions of boxes in the box lists.  The
    ## function applyCropList then just ignores the cropping information for any
    ## pages which were not selected.
    ##

    allPageNums = set(range(0, inputDoc.getNumPages()))
    pageNumsToCrop = set()
    if args.pages:
        for pageNumOrRange in args.pages.split(","):
            splitRange = pageNumOrRange.split("-")
            try:
                if len(splitRange) == 1:
                    # Note pyPdf page nums start at 0, not 1 like usual PDF pages,
                    # subtract 1.
                    pageNumsToCrop.add(int(splitRange[0])-1)
                else:
                    pageNumsToCrop.update(
                        set(range(int(splitRange[0])-1, int(splitRange[1]))))
            except ValueError:
                print(
                    "\nError in pdfCropMargins: The page range specified on the command",
                    "\nline contains a non-integer value or otherwise cannot be parsed.",
                    file=sys.stderr)
                ex.cleanupAndExit(1)
        pageNumsToCrop = pageNumsToCrop & allPageNums # intersect chosen with actual
    else:
        pageNumsToCrop = allPageNums

    # Print out the pages to crop in verbose mode.
    if args.verbose and args.pages:
        print("These pages of the document will be cropped:", end="")
        pNumList = sorted(list(pageNumsToCrop))
        for i in range(len(pNumList)):
            if i % 10 == 0 and i != len(pNumList)-1: print("\n   ", end="")
            print("%5d" % (pNumList[i]+1), " ", end="")
        print("\n")
    elif args.verbose:
        print("\nAll the pages of the document will be cropped.")

    ##
    ## Get a list with the full-page boxes for each page: (left,bottom,right,top)
    ## This function also sets the MediaBox and CropBox of the pages to the
    ## chosen full-page size as a side-effect, saving the old boxes.
    ##

    fullPageBoxList, rotationList = getFullPageBoxListAssigningMediaAndCrop(inputDoc)
    tmpfullPageBoxList, tmpRotationList = getFullPageBoxListAssigningMediaAndCrop(
                                                            tmpInputDoc, quiet=True)

    ##
    ## Define the PdfFileWriter object and insert all the inputDoc pages into it.
    ## Note that inserting pages from a PdfFileReader into multiple PdfFileWriters
    ## seems to cause problems (writer can hang on write), so only one is used.
    ##

    outputDoc = PdfFileWriter()
    for page in [inputDoc.getPage(i) for i in range(inputDoc.getNumPages())]:
        outputDoc.addPage(page)

    tmpOutputDoc = PdfFileWriter()
    for page in [tmpInputDoc.getPage(i) for i in range(tmpInputDoc.getNumPages())]:
        tmpOutputDoc.addPage(page)

    ##
    ## Write out the PDF document again, with the CropBox and MediaBox reset.
    ## This temp version is only used for calculating the bounding boxes of
    ## pages.  Note we are writing from tmpOutputDocument (due to an apparent bug
    ## discussed above).  After this tmpInputDoc and tmpOutputDoc are no longer
    ## needed.
    ##

    if not args.restore:
        docWithCropAndMediaBoxesName = ex.getTemporaryFilename(".pdf")
        docWithCropAndMediaBoxesObject = open(docWithCropAndMediaBoxesName, "wb")

        if args.verbose:
            print("\nWriting out the PDF with the CropBox and MediaBox redefined.")

        try:
            tmpOutputDoc.write(docWithCropAndMediaBoxesObject)
        except KeyError:
            print("\nError in pdfCropMargins: The pyPdf program failed in trying to"
                  "\nwrite out a PDF file of the document.  The document may be"
                  "\ncorrupted.  If you have Ghostscript, try using the '--gsFix'"
                  "\noption (assuming you are not already using it).", file=sys.stderr)
            ex.cleanupAndExit(1)

        docWithCropAndMediaBoxesObject.close()

    ##
    ## Copy the metadata from inputDot to outputDoc, modifying the Producer string
    ## if this program didn't already set it.  Get bool for whether this program
    ## cropped the document already.
    ##

    alreadyCroppedByThisProgram = setCroppedMetadata(inputDoc, outputDoc,
                                                     metadataInfo)

    ##
    ## Calculate the boundingBoxList containing tight page bounds for each page.
    ##

    if not args.restore:
        boundingBoxList = getBoundingBoxList(docWithCropAndMediaBoxesName, inputDoc,
                             fullPageBoxList, pageNumsToCrop, args, PdfFileWriter)
        if args.verbose:
            print("\nThe bounding boxes are:")
            for pNum, b in enumerate(boundingBoxList):
                print("\t", pNum+1, "\t", b)

    ##
    ## Calculate the cropList based on the fullpage boxes and the bounding boxes.
    ##

    if not args.restore:
        cropList = calculateCropList(fullPageBoxList, boundingBoxList,
                                     rotationList, pageNumsToCrop)
    else:
        cropList = None # not needed in this case

    ##
    ## Apply the calculated crops to the pages of the PdfFileReader inputDoc.
    ## This also modifies the same pages in the PdfFileWriter outputDoc.
    ##

    applyCropList(cropList, inputDoc, pageNumsToCrop, alreadyCroppedByThisProgram)

    ##
    ## Write the final PDF out to a file.
    ##

    if args.verbose: print("\nWriting the cropped PDF file.")

    outputDocStream = open(outputDocFname, "wb")
    try:
        outputDoc.write(outputDocStream)
    except KeyError:
        print("\nError in pdfCropMargins: The pyPdf program failed in trying to"
              "\nwrite out a PDF file of the document.  The document may be"
              "\ncorrupted.  If you have Ghostscript, try using the '--gsFix'"
              "\noption (assuming you are not already using it).", file=sys.stderr)
        ex.cleanupAndExit(1)
    # Experimental test in line below to catch if it hangs... still causes bugs...
    #completed = ex.functionCallWithTimeout(outputDoc.write, [outputDocStream], secs=0)
    outputDocStream.close()
    completed = True
    if not completed:
        print("Sorry, the PDF writer is taking longer than the timeout time.  Exiting.",
              file=sys.stderr)
        ex.cleanupAndExit(1)

    # We're finished with this open file; close it; let temp dir removal delete it.
    fixedInputDocFileObject.close()

    ##
    ## Now handle the options which apply after the file is written.
    ##

    def doPreview(outputDocFname):
        viewer = args.preview
        if args.verbose:
            print("\nPreviewing the output document with viewer:\n   ", viewer)
        ex.showPreview(viewer, outputDocFname)
        return

    # Handle the '--queryModifyOriginal' option.
    if args.queryModifyOriginal:
        if args.preview:
            print("\nRunning the preview viewer on the file, will query whether or not"
                  "\nto modify the original file after the viewer is launched in the"
                  "\nbackground...\n")
            doPreview(outputDocFname)
            # Give preview time to start; it may write startup garbage to the terminal...
            queryWaitTime = 1 # seconds
            time.sleep(queryWaitTime)
            print()
        while True:
            queryString = "\nModify the original file to the cropped file " \
                "(saving the original)? [yn] "
            if ex.pythonVersion[0] == "2":
                queryResult = raw_input(queryString).decode("utf-8")
            else:
                queryResult = input(queryString)
            if queryResult in ["y", "Y"]:
                args.modifyOriginal = True
                print("\nModifying the original file.")
                break
            elif queryResult in ["n", "N"]:
                print("\nNot modifying the original file.  The cropped file is saved"
                      " as:\n   {0}".format(outputDocFname))
                args.modifyOriginal = False
                break
            else:
                print("Response must be in the set {y,Y,n,N}, none recognized.")
                continue

    # Handle the '--modifyOriginal' option.
    if args.modifyOriginal:
        generatedUncroppedFilename = generateDefaultFilename(
                                                  inputDocFname, isCroppedFile=False)

        # Remove any existing file with the name generatedUncroppedFilename unless a
        # relevant noclobber option is set or it isn't a file.
        if os.path.exists(generatedUncroppedFilename):
            if os.path.isfile(generatedUncroppedFilename) \
                    and not args.noclobberOriginal and not args.noclobber:
                if args.verbose:
                    print("\nRemoving the file\n   ", generatedUncroppedFilename)
                # TODO may want try-except on this; permissions
                os.remove(generatedUncroppedFilename)
            else:
                print(
                    "\nA noclobber option is set or not a file; refusing to"
                    " overwrite:\n   ", generatedUncroppedFilename,
                    "\nFiles are as if option '--modifyOriginal' were not set.",
                    file=sys.stderr)

        # Move (noclobber) the original file to the name for uncropped files.
        if not os.path.exists(generatedUncroppedFilename):
            if args.verbose: print("\nDoing a file move:\n   ", inputDocFname,
                                   "\nis moving to:\n   ", generatedUncroppedFilename)
            shutil.move(inputDocFname, generatedUncroppedFilename)

        # Move (noclobber) the cropped file to the original file's name.
        if not os.path.exists(inputDocFname):
            if args.verbose: print("\nDoing a file move:\n   ", outputDocFname,
                                   "\nis moving to:\n   ", inputDocFname)
            shutil.move(outputDocFname, inputDocFname)

    # Handle any previewing which still needs to be done.
    if args.preview and not args.queryModifyOriginal: # already previewed in query mod
        if args.modifyOriginal: # already swapped to original filename in this case
            doPreview(inputDocFname)
        else: # the usual case, preview the output filename
            doPreview(outputDocFname)

    if args.verbose: print("\nFinished this run of pdfCropMargins.\n")

    return

