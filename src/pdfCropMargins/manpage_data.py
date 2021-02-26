"""

pdfCropMargins -- a program to crop the margins of PDF files

This module sets up an argparse command-line parser, named `cmd_parser`, meant for
use with the prettifying routines in `prettified_argparse.py`.  The command-line
arguments, flags, and their descriptions are all defined here.  The formatting
used here assumes that the prettified formatting directives from
`prettified_argparse.py` are being used.

The usage is::

   from prettified_argparse import parse_command_line_arguments
   from manpage_data import cmd_parser

Somewhere in the program, the function should be called as::

    args = parse_command_line_arguments(cmd_parser)

Note that the default text formatting in the description is raw, i.e., it is
unformatted unless the formatting directive ^^f is specified.  So literal
'%' characters can be used.  The option descriptions are not raw, however,
and so '%' characters must be escaped as '%%'.

General argparse reminders and warnings:
  1) Using `nargs=1` puts the single value inside a list, default doesn't.
  2) First argument specified is the one which appears in the Usage message.
  3) The metavar kwarg sets the string for option's VALUES in Usage messages.
  4) With default values you can always assume some value is assigned.
  5) Use `numargs=1` and `default=[]` to test whether or not, say, an int-valued
     option was selected at all (or you could check for value None).

=====================================================================

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

import argparse
import sys
from . import __version__ # Get the version number from the __init__.py file.

DEFAULT_THRESHOLD_VALUE = 191

description = """
Description:

^^f
   A command-line application to crop the margins of PDF files.  Cropping the
   margins can make it easier to read the pages of a PDF document -- whether
   the document is printed or displayed on a screen -- because the display
   fonts are larger.  Margin-cropping is also sometimes useful when a PDF file
   is included in a document as a graphic.

   By default 10% of the existing margins will be retained; the rest will be
   eliminated.  There are many options which can be set, however, including the
   percentage of existing margins to retain.

   Here is a simple example of cropping a file named document.pdf and writing
   the cropped output-document to a file named croppedDocument.pdf:

   \a\a\apdf-crop-margins document.pdf -o croppedDocument.pdf

   If no destination is provided a filename will be automatically generated
   from the name of the source file (see below).

   The pdfCropMargins program works by changing the page sizes which are stored
   in the PDF file (and are interpreted by programs like Acrobat Reader).
   Both the CropBox and the MediaBox are set to the newly-computed cropped
   size.  After this the view of the document in most programs will be the new,
   cropped view.

   In order to reduce the number of copies of a document which must be saved, a
   basic '--restore' option is provided.  When cropping a file not produced by
   the pdfCropMargins program the default is to save the intersection of the
   MediaBox and any existing CropBox in the ArtBox.  This saves the "usual"
   view of the original document in programs like Acrobat Reader.  Subsequent
   crops of a file produced by pdfCropMargins do not by default alter the
   ArtBox.  The restore option simply copies the saved values back to the
   MarginBox and CropBox.  Note that this assumes the ArtBox is unused (it is
   rarely used, and this feature can be turned off with the -A option).  So,
   for example, you can make annotations to a file with cropped margins and
   still produce a version with the annotations which viewers display as the
   original margins.  Programs which change the "Producer" string in the PDF
   may interfere with this feature.

   Below are several examples using more of the command-line options, each
   applied to an input file called doc.pdf.  The output filename is unspecified
   in most of these examples, so the program will automatically generate the
   filename (or an output filename can always be explicitly provided with '-o'):
^^f

     1) Crop doc.pdf so that all the pages are set to the same size and the
     cropping amount is uniform across all the pages (this gives a nice two-up
     appearance).  The default of retaining 10% of the existing margins is
     used.  Note carefully that '-u' only makes the amount to be cropped uniform
     for each page; if the pages do not have the same size to begin with they
     will not have the same size afterward unless the '-s' option is also used.

        pdf-crop-margins -u -s doc.pdf

     2) Crop each page of doc.pdf individually (i.e., not uniformly), keeping 50%
     of the existing margins.

        pdf-crop-margins -p 50 doc.pdf

     3) Crop doc.pdf uniformly, keeping 50% of the left margin, 20% of the bottom
     margin, 40% of the right margin, and 10% of the top margin.

        pdf-crop-margins -u -p4 50 20 40 10 doc.pdf

     4) Crop doc.pdf retaining 20% of the margins, and then reduce the right page
     margins only by an absolute 12 points.

        pdf-crop-margins -p 20 -a4 0 0 12 0 doc.pdf

     5) Add a constant 5bp around the bare bounding boxes on all pages (note the
     negative value passed to the `-a` option, which adds space rather than
     removing it).

        pdf-crop-margins -p 0 -a -5 doc.pdf

     6) Pre-crop the document by 5bp on each side before computing the bounding
     boxes.  Then crop retaining 50% of the computed margins.  This can be
     useful for difficult documents such as scanned books with page-edge noise
     or other "features" inside the current margins.

        pdf-crop-margins -ap 5 -p 50 doc.pdf

     7) Crop doc.pdf, re-naming the cropped output file to doc.pdf and backing
     up the original file in a file named backup_doc.pdf.

        pdf-crop-margins -mo -pf -su "backup" doc.pdf

     8) Crop the margins of doc.pdf to 120% of their original size, increasing
     the margins.  Use Ghostscript to find the bounding boxes without explicit
     rendering by pdfCropMargins.

        pdf-crop-margins -p 120 -c gb doc.pdf

     9) Crop the margins of doc.pdf ignoring the 10 largest margins on each edge
     (over the whole document).  This is especially good for noisy documents
     where all the pages have very similar margins, or when you want to ignore
     marginal annotations which only occur on a few pages.

        pdf-crop-margins -m 10 doc.pdf

     10) Crop doc.pdf, launch the acroread viewer on the cropped output, and then
     query as to whether or not to rename the cropped file doc.pdf and back up
     the original file as doc_uncropped.pdf.

        pdf-crop-margins -mo -q doc.pdf

     11) Crop pages 1-100 of doc.pdf, cropping all even pages uniformly and all odd
     pages uniformly.

        pdf-crop-margins -g 1-100 -e doc.pdf

     12) Try to restore doc.pdf to its original margins, assuming it was cropped
     with pdfCropMargins previously.  Note that the default output filename is
     still named doc_cropped.pdf, even though it is the recovered file.  Use the
     '-mo' option to modify doc.pdf and backup the previous version.

        pdf-crop-margins -r doc.pdf

^^f
   There are many different ways to use this program.  After finding a method
   which works well for a particular task or workflow pattern it is often
   convenient to make a simple shell script (batch file) which invokes the
   program with those particular options and settings.  Simple template scripts
   for Bash and Windows are packaged with the program, in the bin directory.
   The program can also be called from a user's Python program (when discoverable
   in the Python path) by using code such as
^^f

        from pdfCropMargins import crop
        crop(["-p", "20", "-u", "-s", "paper.pdf"])

^^f
   When printing a document with closely-cropped pages it may be necessary to
   use options such as "Fit to Printable Area".  It may also be necessary to
   fine-tune the size of the retained margins if the edges of the text are
   being cut off.

   Sometimes a PDF file is corrupted or non-standard to the point where the
   routines used by this program raise an error and exit.  In that case it can
   sometimes help to repair the PDF file before attempting to crop it.  If it
   is readable by Ghostscript then the following command will often repair
   it sufficiently:
^^f

        gs -o repaired.pdf -sDEVICE=pdfwrite -dPDFSETTINGS=/prepress corrupted.pdf

^^f
   This command can also be used to convert some PostScript (.ps) files to PDF.
   The option '--gsFix' (or '-gsf') will automatically attempt to apply this
   fix, provided Ghostscript is available.  See the description of that option
   for more information.

   The pdfCropMargins program handles rotated pages (such as pages in landscape
   mode versus portrait mode) as follows.  All rotated pages are un-rotated as
   soon as they are read in.  All the cropping is then calculated.  Finally, as
   the crops are applied to the pages, the rotation is re-applied.  This may
   give unexpected results in documents which mix pages at different rotations,
   especially with the '--uniform' or '--samePageSize' options.  For rotated
   pages the arguments of all the options which take four arguments, one for
   each margin, are shifted so the left, bottom, right, and top margins
   correspond to the screen appearance (regardless of any internal rotation).

   All the command-line options to pdfCropMargins are described below.  The
   following definition is useful in precisely defining what several of the
   options do.  The "delta values" are the absolute reduction lengths, in
   points, which are applied to each original page to get the final cropped
   page.  There is a delta value for each margin, on each page.  In the usual
   case where all the margin sizes decrease, all the deltas are positive.  A
   delta value can, however, be negative (e.g., when percentRetain > 100 or
   when a negative absolute offset is used).  When a delta value is negative
   the corresponding margin size will increase.
^^f
   """

epilog = """The pdfCropMargins program is Copyright (c) 2014 by Allen Barker.
Released under the GNU GPL license, version 3 or later."""

def formatter_class(prog):
    #return argparse.RawTextHelpFormatter(prog, max_help_position=10, width=80)
    return argparse.RawDescriptionHelpFormatter(prog,
                           max_help_position=15, width=None)

# Consider adding `usage` argument to ArgumentParser.
if sys.version_info[0:3] >= (3,5):
    cmd_parser = argparse.ArgumentParser(allow_abbrev=False,
        formatter_class=formatter_class,
        description=description, epilog=epilog,
        prog="pdf-crop-margins")
else:
    cmd_parser = argparse.ArgumentParser(
        formatter_class=formatter_class,
        description=description, epilog=epilog,
        prog="pdf-crop-margins")


cmd_parser.add_argument("pdf_input_doc", nargs="+", metavar="PDF_FILE", help="""

   The pathname of the PDF file to crop.  Use quotes around any file or
   directory name which contains a space.  If no filename is given for the
   cropped PDF output file via the '-o' flag then a default output filename
   will be generated.  By default it is the same as the source filename except
   that the suffix ".pdf" is replaced by "_cropped.pdf", overwriting by default
   if the file already exists.  The file will be written to the working
   directory at the time when the program was run.  If the input file has no
   extension or has an extension other than '.pdf' or '.PDF' then the suffix
   '.pdf' will be appended to the existing (possibly-null) extension.  Globbing
   of wildcards and shell variable expansions are performed on the path.^^n""")

cmd_parser.add_argument("-o", "--outfile", nargs=1,
                        metavar="OUTFILE_PATH_OR_DIR", default=[], help="""

   An optional argument specifying the directory or file path that the cropped
   output document should be written to.  If this option is not given the
   program will generate an output filename from the input filename and write
   to the current working directory.  By default the string "_cropped" is
   appended to the input filename just before the file extension.  (If the
   extension is not '.pdf' or '.PDF' then '.pdf' is also appended to the
   extension.)  The options '--usePrefix', '--stringCropped' and
   '--stringSeparator' can be used to customize the generated filenames.  By
   default any existing file with the same name will be silently overwritten;
   this can be avoided with the '--noclobber' option.  Globbing of wildcards
   and shell variable expansions are performed on the directory path but not on
   the filename part.^^n""")

cmd_parser.add_argument("-v", "--verbose", action="store_true", help="""

   Print more information about the program's actions and progress.  Without
   this switch only warning and error messages are printed to the
   screen.^^n""")

cmd_parser.add_argument("-gui", "--gui", action="store_true", help="""

   Run the graphical user interface.  This mode allows you to interactively
   preview and test different cropping options without having to recalculate
   the bounding boxes each time (which can be slow).  All the usual
   command-line options to the program are still respected.  Clicking the
   'Crop' button in the GUI crops with the current settings, writing out a
   cropped PDF file to the same filename that the command-line version would
   write to.  Note that successive changes to the margins in the GUI are not
   cumulative: settings are always applied to the original document as it was
   passed in to the program.  The 'Original' button reverts the display back to
   that original version.^^n""")

cmd_parser.add_argument("-p", "--percentRetain", nargs=1, type=float,
                        metavar="PCT", default=[10.0], help="""

   Set the percent of margin space to retain in the image.  This is a
   percentage of the original margin space.  By default the percent value is
   set to 10.  Setting the percentage to 0 gives a tight bounding box.  Percent
   values greater than 100 increase the margin sizes from their original sizes,
   and negative values decrease the margins even more than a tight bounding
   box.^^n""")

cmd_parser.add_argument("-p4", "-pppp", "--percentRetain4", nargs=4,
                        type=float, metavar="PCT", help="""

   Set the percent of margin space to retain in the image, individually for the
   left, bottom, right, and top margins, respectively.  The four arguments
   should be percent values.^^n""")

cmd_parser.add_argument("-pt", "--percentText", action="store_true", help="""

   Normally the percentage values passed to '--percentRetain' or
   '--percentRetain4' define the percentage of existing margins to retain.
   This flag alters the interpretation of those percent values.  The margins
   are instead set to the given percentage of the text width or height.  The
   left and right margins are set to a percentage of the bounding box width and
   the bottom and top margins are set to a percentage of the bounding box
   height.^^n""")

cmd_parser.add_argument("-a", "--absoluteOffset", nargs=1, type=float,
                        metavar="BP", default=[0.0], help="""

   Decrease each margin size by an absolute floating point offset value, to be
   subtracted from each margin's size after the 'percentRetain' option is
   applied.  The units are big points, bp, which is the unit used in PDF files.
   There are 72 bp in an inch.  A single bp is approximately equal to a TeX
   point, pt (with 72.27pt in an inch).  Negative values are allowed; positive
   numbers always decrease the margin size and negative numbers always increase
   it.  Absolute offsets are always applied after any percentage change
   operations.^^n""")

cmd_parser.add_argument("-a4", "-aaaa", "--absoluteOffset4", nargs=4,
                        type=float, metavar="BP", help="""

   Decrease the margin sizes individually with four absolute offset values.
   The four floating point arguments should be the left, bottom, right, and top
   offset values, respectively.  See the '--absoluteOffset' option for
   information on the units.^^n""")

# Note the percent sign in text below needs to be a double percent or argument
# parsing breaks.
cmd_parser.add_argument("-ap", "--absolutePreCrop", nargs=1, type=float,
                        metavar="BP", default=[0.0], help="""

   This option is like '--absoluteOffset' except that it is applied before any
   bounding box calculations (or any other operations).  The argument is the
   same, in units of bp.  All successive operations are then relative to this
   pre-crop box, considered to be the full-page box.  Note that since this
   absolute crop is applied before any bounding boxes are computed it is
   relative to the original full-page boxes of the document (unlike
   'absoluteOffset', which is a crop relative to the newly-cropped margin after
   'percentRetain' is applied).  As a consequence, the number of points may
   need to be larger than what would work for 'absoluteOffset'.  This option
   can be used to ignore text and markings out at the edge of the margins by
   cropping it out before the bounding boxes are calculated.^^n""")

cmd_parser.add_argument("-ap4", "--absolutePreCrop4", nargs=4, type=float,
                        metavar="BP", help="""

   This is the same as '--absolutePreCrop' except that four separate arguments
   can be given.  The four floating point arguments should be the left, bottom,
   right, and top absolute pre-crop values, respectively.^^n""")

cmd_parser.add_argument("-u", "--uniform", action="store_true", help="""

   Crop all the pages uniformly.  This forces the magnitude of margin-cropping
   (absolute, not relative) to be the same on each page.  This option is
   applied after all the delta values have been calculated for each page,
   individually.  Then all the left-margin delta values, for each page, are set
   to the smallest left-margin delta value over every page.  The bottom, right,
   and top margins are processed similarly.  Note that this effectively adds
   some margin space (relative to the margins obtained by cropping pages
   individually) to some of the pages.  If the pages of the original document
   are all the same size then the cropped pages will again all be the same
   size.  The '--samePageSize' option can be used in combination with this
   option to force all pages to be the same size after cropping.^^n""")

cmd_parser.add_argument("-m", "--uniformOrderStat", nargs=1, type=int,
                        default=[], metavar="INT", help="""

   Choosing this option implies the '--uniform' option, but the smallest delta
   value over all the pages is no longer chosen.  Instead, for each margin the
   nth smallest delta value (with n numbered starting at zero) is chosen over
   all the pages.  The argument is the integer n, for example '-m 4'.  Choosing
   n to be half the number of pages gives the median delta value.  This option
   is useful for cropping noisy scanned PDFs which have a common margin size on
   most of the pages, or for ignoring annotations which only appear in the
   margins of a few pages.  This option essentially causes the program to
   ignores the n largest tight-crop margins when computing common delta values
   over all the pages.  Increasing n always either increases the cropping
   amount or leaves it unchanged.  Some trial-and-error may be needed to choose
   the best number.  Using '-m 1' tends to work well with arXiv papers (which
   have a date in the margin of the first page).^^n""")

cmd_parser.add_argument("-m4", "-mmmm", "--uniformOrderStat4", nargs=4,
                        type=int, default=[], metavar="INT", help="""

   This option is the same as '--uniformOrderStat' (or '-m') except that
   separate values are specified for each margin individually.  The margins are
   ordered as left, bottom, right, and top.^^n""")

cmd_parser.add_argument("-mp", "--uniformOrderPercent", nargs=1, type=float,
                        default=[], metavar="INT", help="""

   This option is the same as '--uniformOrderStat' except that the order number
   n is automatically set to a given percentage of the number of pages which
   are set to be cropped (either the full number or the ones set with
   '--pages').  This option overrides '--uniformOrderStat' if both are set.
   The argument is a float percent value; rounding is done to get the final
   order-number.  Setting the percent to 0 is equivalent to n=1, setting the
   percent to 100 is equivalent to setting n to the full number of pages, and
   setting the percent to 50 gives the median (for odd numbers of
   pages).^^n""")

cmd_parser.add_argument("-s", "--samePageSize", action="store_true", help="""

   Set all the page sizes to be equal.  This option only has an effect when the
   page sizes are different.  The pages sizes are set to the size of the union
   of all the page regions, i.e., to the smallest bounding box which contains
   all the pages.  This operation is always done before any others (except
   '--absolutePreCrop').  The cropping is then done as usual, but note that any
   margin percentages (such as for '--percentRetain') are now relative to this
   new, possibly larger, page size.  The resulting pages are still cropped
   independently by default, and will not necessarily all have the same size
   unless '--uniform' is also selected to force the cropping amounts to be the
   same for each page.  If pages are selected with '--pages' then this option
   is only applied to those selected pages.^^n""")

cmd_parser.add_argument("-ms", "--samePageSizeOrderStat", nargs=1, type=int,
                        default=[], metavar="INT", help="""

   Choosing this option implies the '--samePageSize' option, but the
   calculations for each edge of the smallest bounding box ignore the largest
   (or smallest for left and bottom edges) n values.  The argument is the
   nonnegative number n.  Each edge is calculated independently.  This is an
   order statistic for selecting the uniform size to make the pages.  Note that
   this will cut off parts of some pages if n>0.^^n""")

cmd_parser.add_argument("-e", "--evenodd", action="store_true", help="""

   Crop all the odd pages uniformly, and all the even pages uniformly.  The
   largest amount of cropping that works for all the pages in each group is
   chosen.  If the '--uniform' ('-u') option is simultaneously set then the
   vertical cropping will be uniform over all the pages and only the
   horizontal cropping will differ between even and odd pages.^^n""")

cmd_parser.add_argument("-g", "-pg", "--pages", metavar="PAGESTR", help="""

   Apply the cropping operation only to the selected pages.  The argument
   should be a list of the usual form such as "2-4,5,9,20-30".  The
   page-numbering is assumed to start at 1.  Ordering in the argument list is
   unimportant, negative ranges are ignored, and pages falling outside the
   document are ignored.  Note that restore information is always saved for all
   the pages (in the ArtBox) unless '--noundosave' is selected.^^n""")

cmd_parser.add_argument("-c", "--calcbb", choices=["d", "m", "p", "gr", "gb", "o"],
                       metavar="[d|m|p|gr|gb|o]", default="d", help="""

   Choose the method to calculate bounding boxes (or to render the PDF pages in
   order to calculate the boxes).  The default option 'd' will choose the MuPDF
   rendering option if the PyMuPDF dependency is installed, otherwise it will
   use pdftoppm rendering or Ghostscript rendering, in that order, if the
   external programs can be located.  The options to force a particular method
   are MuPDF ('m'), pdftoppm ('p'), or Ghostscript ('gr') for rendering, or
   direct Ghostscript bounding-box calculation ('gb').  For pdftoppm or
   Ghostscript options the corresponding program must be installed and
   locatable (see the path-setting options below if the default locator fails).
   Only the explicit rendering methods will work for scanned pages (see
   '--gsBbox').  Choosing 'o' reverts to the old default behavior of first
   looking for pdftoppm and then looking for Ghostscript for rendering.^^n""")

cmd_parser.add_argument("-gs", "--gsBbox", action="store_true", help="""

   This option is maintained for backward compatibility; using '-c gb' is now
   preferred.  Use Ghostscript to directly find the bounding boxes for the
   pages, with no explict rendering of the pages.  (The default is to
   explicitly render the PDF pages to image files and calculate bounding boxes
   from the images.) This method tends to be much faster, but it does not work
   with scanned PDF documents.  It also does not allow for choosing the
   threshold value, applying blurs, etc.  Any resolution options are passed to
   the Ghostscript bbox device.  This option requires that Ghostscript be
   available in the PATH as "gswin32c.exe" or "gswin64c.exe" on Windows, or as
   "gs" on Linux.  When this option is set the Pillow image library for Python
   is not required.^^n""")

cmd_parser.add_argument("-gsr", "--gsRender", action="store_true", help="""

   This is maintained for backward compatibility; using '-c gr' is now
   preferred.  Use Ghostscript to render the PDF pages to images.  By default
   the pdftoppm program will be preferred for the rendering, if it is found.
   Note that this option has no effect if '--gsBbox' is chosen, since then no
   explicit rendering is done.^^n""")

cmd_parser.add_argument("-t", "--threshold", type=int, nargs=1,
               default=[DEFAULT_THRESHOLD_VALUE], metavar="BYTEVAL", help="""

   Set the threshold for determining what is background space (white).  The
   value can be from 0 to 255, with 191 the default (75 percent).  This option
   may not be available for some configurations since the PDF must be
   internally rendered as an image of pixels.  In particular, it is ignored
   when '--gsBbox' is selected.  Any pixel value over the threshold is
   considered to be background (white), and any value below it is considered to
   be text (black).  Lowering the value should tend to make the bounding boxes
   smaller.  The threshold may need to be lowered, for example, for scanned
   images with greyish backgrounds.  For pages with dark backgrounds and light
   text a negative threshold value can be used.  In that case the absolute
   value is used as the threshold but the test is reversed to consider pixel
   values greater than or equal to the threshold to be background.^^n""")

cmd_parser.add_argument("-nb", "--numBlurs", type=int, default=0, metavar="INT",
                        help="""

   When PDF files are explicitly rendered to image files, apply a blur
   operation to the resulting images this many times.  This can be useful for
   noisy images.^^n""")

cmd_parser.add_argument("-ns", "--numSmooths", type=int, default=0, metavar="INT",
                        help="""

   When PDF files are explicitly rendered to image files, apply a smoothing
   operation to the resulting images this many times.  This can be useful for
   noisy images.^^n""")

cmd_parser.add_argument("-x", "--resX", type=int, default=72,
                        metavar="DPI", help="""

   The x-resolution in dots per inch to use when the image is rendered to find
   the bounding boxes.  The default is 150.  Higher values produce more precise
   bounding boxes but require more time and memory.^^n""")

cmd_parser.add_argument("-y", "--resY", type=int, default=72,
                        metavar="DPI", help="""

   The y-resolution in dots per inch to use when the image is rendered to find
   the bounding boxes.  The default is 150.  Higher values produce more precise
   bounding boxes but require more time and memory.^^n""")

cmd_parser.add_argument("-b", "--boxesToSet", choices=["m", "c", "t", "a", "b"],
                        metavar="[m|c|t|a|b]", action="append", default=[], help="""

   By default the pdfCropMargins program sets both the MediaBox and the CropBox
   for each page of the cropped PDF document to the new, cropped page size.
   This default setting is usually sufficient, but this option can be used to
   select different PDF boxes to set.  The option takes one argument, which is
   the first letter (lowercase) of a type of box.  The choices are MediaBox
   (m), CropBox (c), TrimBox (t), ArtBox (a), and BleedBox (b).  This option
   overrides the default and can be repeated multiple times to set several box
   types.^^n""")

cmd_parser.add_argument("-f", "--fullPageBox", choices=["m", "c", "t", "a", "b"],
                        metavar="[m|c|t|a|b]", action="append", default=[], help="""

   By default the program first (before any cropping is calculated) sets the
   MediaBox and CropBox of each page in (a copy of) the document to the
   intersection of its previous MediaBox and CropBox.   This ensures that the
   cropping is relative to the usual document-view in programs like Acrobat
   Reader.   This essentially defines what is assumed to be the full size of
   pages in the document, and all cropping is then performed relative to that
   full-page size.  This option can be used to alternately use the MediaBox,
   the CropBox, the TrimBox, the ArtBox, or the BleedBox in defining the
   full-page size.  The option takes one argument, which is the first letter
   (lowercase) of the type of box to use.  If the option is repeated then the
   intersection of all the box arguments is used.  Only one choice is allowed
   in combination with the '-gs' option since Ghostscript does its own internal
   rendering when finding bounding boxes.  The default with '-gs' is the
   CropBox.^^n""")

cmd_parser.add_argument("-r", "--restore", action="store_true", help="""

   This is a simple undo operation which essentially undoes all the crops ever
   made by pdfCropMargins and returns to the original margins (provided no
   other program modified the Producer metadata or ArtBoxes).  By default,
   whenever this program crops a file for the first time it saves the MediaBox
   intersected with the CropBox as the new ArtBox (since the ArtBox is rarely
   used).  The Producer metadata is checked to see if this was the first time.
   If so, the ArtBox for each page is simply copied to the MediaBox and the
   CropBox for the page.  This restores the earlier view of the document, such
   as in Acrobat Reader (but does not completely restore the previous condition
   in cases where the MediaBox and CropBox differed or the ArtBox had a
   previous value).  Any options such as '-u', '-p', and '-a' which do not make
   sense in a restore operation are ignored.  Note that as far as default
   filenames the operation is treated as just another crop operation (the
   default-generated output filename still has a "_cropped.pdf" suffix).  The
   '--modifyOriginal' option (or its query variant) can be used with this
   option.  Saving in the ArtBoxes can be disabled by using the '--noundosave'
   option.^^n""")

# Maybe later: an option to choose which box to save to, or none, rather
# than just turn off ArtBox.
cmd_parser.add_argument("-A", "--noundosave", action="store_true", help="""

   Do not save any restore data in the ArtBox.  This option will need to be
   selected if the document actually uses the ArtBox for anything important
   (which is rare).  Note that the '--restore' operation will not work
   correctly for the cropped document if this option is included in the
   cropping command.  (The program does not currently check for this when doing
   a restore.)^^n""")

cmd_parser.add_argument("-gsf", "--gsFix", action="store_true", help="""

   Attempt to repair the input PDF file with Ghostscript before it is read-in
   with PyPdf.  This requires that Ghostscript be available.  (See the general
   description text above for the actual command that is run.)  This can also
   be used to automatically convert some PostScript files (.ps) to PDF for
   cropping.  The repaired PDF is written to a temporary file; the original PDF
   file is not modified.  The original filename is treated as usual as far as
   automatic name-generation, the '--modify-original' option, and so forth.
   This option is often helpful if the program hangs or raises an error due to
   a corrupted PDF file.  Note that when re-cropping a file already cropped by
   pdfCropMargins this option is probably not necessary, and if it is used in a
   re-crop (at least with current versions of Ghostscript) it will reset the
   Producer metadata which the pdfCropMargins program uses to tell if the file
   was already cropped by the program (so the '--restore' option will not work
   in combination with this option).  This option is not recommended as
   something to use by default unless you encounter many corrupted PDF files
   and do not need to restore back to the original margins.^^n""")

cmd_parser.add_argument("-nc", "--noclobber", action="store_true", help="""

   Never overwrite an existing file with the cropped output file.^^n""")

cmd_parser.add_argument("-pv", "--preview", metavar="PROG", help="""

   Run a PDF viewer on the cropped PDF output.  The viewer process is run in
   the background.  The viewer is launched after pdfCropMargins has finished
   all the other options.  The only exception is when the '--queryModifyOriginal'
   option is also selected.  In that case the viewer is launched before the
   query so that the user can look at the output before deciding whether or not
   to modify the original.  (Note that answering 'y' will then move the file
   out from under the running viewer; close and re-open the file before adding
   annotations, highlighting, etc.)  The single argument should be the path of
   the executable file or script to run the chosen viewer.  The viewer is
   assumed to take exactly one argument, a PDF filename.  For example, on Linux
   the Acrobat Reader could be chosen with /usr/bin/acroread or, if it is in
   the PATH, simply acroread.  A shell script or batch file wrapper can be used
   to set any additional options for the viewer.^^n""")

cmd_parser.add_argument("-mo", "--modifyOriginal", action="store_true", help="""

   This option moves (renames) the original document file to a backup filename
   and then moves the cropped file to the original document's filename (and
   directory path).  Thus it effectively crops the original document file
   in-place and makes a backup copy of the original file in the output
   directory.  The backup filename for the original document is always
   generated from the original filename; any prefix or suffix which would be
   added by the program to generate a filename (by default a "_cropped" suffix)
   is modified accordingly (by default to "_uncropped").  The '--usePrefix',
   '--stringUncropped', and '--stringSeparator' options can all be used to
   customize the generated backup filename.  If an output path is specified via
   the '--outfile' ('-o') option then the backup document is written to that
   directory (the same directory the cropped file was first written to).  This
   operation is performed last, so if a previous operation fails the original
   document will be unchanged.  Be warned that running pdfCropMargins twice on
   the same source path with this option will modify the backed-up original
   file; the '--noclobberOriginal' option can be used to avoid this.^^n""")

cmd_parser.add_argument("-q", "--queryModifyOriginal", action="store_true",
                        help="""

   This option selects the '--modifyOriginal' option, but queries the user
   about whether to actually do the final move operation.  This works well with
   the '--preview' or '--gui' options: if the preview looks good you can opt to
   modify the original file (keeping a copy of the original). If you decline
   then the files are not swapped (and are just as if the '--modifyOriginal'
   option had not been set).^^n""")

cmd_parser.add_argument("-nco", "--noclobberOriginal", action="store_true",
                        help="""

   If the '--modifyOriginal' option is selected, do not ever overwrite an
   existing file as the backup copy for the original file.  This essentially
   does the move operations for the '--modifyOriginal' option in noclobber
   mode, and prints a warning if it fails.  On failure the result is exactly as
   if the '--modifyOriginal' option had not been selected.  This option is
   redundant if the ordinary '--noclobber' option is also set.^^n""")

cmd_parser.add_argument("-pf", "--usePrefix", action="store_true", help="""

   Prepend a prefix-string when generating default file names rather than
   appending a suffix-string.  The same string value is used, either the
   default or the one set via the '--stringCropped' or '--stringUncropped'
   option.  With the default values for the other options and no output file
   specified, this option causes the cropped output for the input file
   "document.pdf" to be written to the file named "cropped_document.pdf"
   (instead of to the default filename "document_cropped.pdf").^^n""")

cmd_parser.add_argument("-sc", "--stringCropped", default="cropped",
                        metavar="STR", help="""

   This option can be used to set the string which will be appended (or
   prepended) to the document filename when automatically generating the output
   filename for a cropped file.  The default value is "cropped".^^n""")

cmd_parser.add_argument("-su", "--stringUncropped", default="uncropped",
                        metavar="STR", help="""

   This option can be used to set the string which will be appended (or
   prepended) to the document filename when automatically generating the output
   filename for the original, uncropped file.  The default value is
   "uncropped".^^n""")

cmd_parser.add_argument("-ss", "--stringSeparator", default="_", metavar="STR",
                        help="""

   This option can be used to set the separator string which will be used when
   appending or prepending string values to automatically generate filenames.
   The default value is "_".^^n""")

cmd_parser.add_argument("-pw", "--password", metavar="PASSWD", help="""

   Specify a password to be used to decrypt an encrypted PDF file.  Note that
   decrypting with an empty password is always tried, so this option is only
   needed for non-empty passwords.  The resulting cropped file will not be
   encrypted, so use caution if important data is involved.^^n""")

cmd_parser.add_argument("-spr", "--setPageRatios", type=str,
                        default=[], metavar="FLOAT:FLOAT", help="""

   Force all the cropped page ratios to equal the given ratio.  All crops are
   calculated and applied as usual, but either the left and right margins will
   be increased equally or else the top and bottom margins will be increased
   equally in order to make the ratio of width to height equal the set value.
   Margins are only ever increased.  The format for the ratio is either a
   string width-to-height ratio such as '4.5:3' or else a floating point number
   like '0.75' which is the width divided by the height.  This option can be
   useful in some PDF viewers.^^n""")

cmd_parser.add_argument("-prw", "--pageRatioWeights", nargs=4, type=float,
                        default=[1.0,1.0,1.0,1.0], metavar=("FLOAT", "FLOAT",
                        "FLOAT", "FLOAT"), help="""

   This option weights any whitespace added by the '--setPageRatios' argument.
   It takes four weight arguments, one per margin.  The four floating point
   arguments should be the left, bottom, right, and top weights, respectively.
   The weights determine what proportion of the total height(width) increase
   necessary to achieve the target page ratio is added to the corresponding
   margin.  All weights must be greater than zero.^^n""")

cmd_parser.add_argument("-dcb", "--docCatBlacklist", default="",
                        metavar="STR", help="""

   Data associated with the full document, such as outlines, bookmarks, and
   modes, is saved in the document catalog of the PDF file.  By default it is
   all copied over to the cropped document if possible (with some exceptions,
   e.g., "/Pages" will be modified by cropping).  If this is not wanted, or if
   it causes problems for a document, this option specifies a blacklist of
   document catalog items that will never be copied.  The arguments should be
   passed as a single, quoted, whitespace-separated string, for example
   "/Outlines /PageMode /OpenAction".  The special value "ALL" blacklists
   everything.  An empty string blacklists nothing, and is the default.  As an
   example, it can be useful to blacklist "/OpenAction" if on opening the PDF
   it does something like zooming which is not desired.  Blacklisting
   `/PageMode` can also be useful to, for example, not open the outline by
   default.  Running in verbose mode '-v' will show which document catalog
   items are and are not being copied for a document.^^n""")

cmd_parser.add_argument("-dcw", "--docCatWhitelist", default="",
                        metavar="STR", help="""

   See the '--docCatBlacklist' option.  This is just a whitelist that
   essentially works the same way.  The whitelist takes precedence over the
   blacklist.  It specifies a list of items which will always be copied over
   even if they are in the blacklist.  Useful combined with setting the
   blacklist to "ALL" if you only want one or two of the items.  The default
   value is the empty string, which whitelists nothing and so only the
   blacklist is used.  Setting to "ALL" guarantees that everything possible is
   copied over.^^n""")

cmd_parser.add_argument("-i", "--showImages", action="store_true", help="""

   When explicitly rendering PDF files to image files, display the inverse
   image files that are used to find the bounding boxes.  Useful for debugging
   and for choosing some of the other parameters (such as the threshold).  This
   option requires a default external viewer program selected by the Pillow
   image manipulation package (xv on Unix, and usually Paint on Windows).^^n""")

cmd_parser.add_argument("-pdl", "--pdftoppmLocal", action="store_true", help="""

   Use a locally-packaged pdftoppm executable rather than the system version.
   This option is only available on Windows machines; it is ignored otherwise.
   By default the first pdftoppm executable found in the directories in the
   PATH environment variable is used.  On Windows the program will revert to
   this option if PDF image-rendering is required, PyMuPDF is not installed,
   and no system pdftoppm or Ghostscript executable can be found.^^n""")

cmd_parser.add_argument("-gsp", "--ghostscriptPath", type=str, metavar="PATH",
                        default="", help="""

   Pass in a pathname to the ghostscript executable that the program should
   use.  No globbing is done.  Useful when the program is in a nonstandard
   location.^^n""")

cmd_parser.add_argument("-ppp", "--pdftoppmPath", type=str, metavar="PATH",
                        default="", help="""

   Pass in a pathname to the pdftoppm executable that the program should use.
   No globbing is done.  Useful when the program is in a nonstandard
   location.^^n""")

cmd_parser.add_argument("--version", action="version",
                        version="pdfCropMargins {}".format(__version__), help="""

   Return the pdfCropMargins version number and exit immediately.  All
   other options are ignored.^^n""")

cmd_parser.add_argument("-wcdf", "--writeCropDataToFile", type=str,
                        default="", metavar="FILEPATH", help="""

   Write out the calculated list of crops to the file with the file pathname
   that is passed in and exit.  Mostly used for automated testing and
   debugging.^^n""")

