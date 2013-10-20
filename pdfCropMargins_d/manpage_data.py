"""

This module sets up an argparse command-line parser, named cmdParser, meant for
use with the prettifying routines in prettified_argparse.py.  The command-line
arguments, flags, and their descriptions are all defined here.  The formatting
used here assumes that the prettified formatting directives from
prettified_argparse.py are being used.

This file can be copied inline when you really want a single-file script.
Otherwise, the usage is:

   from prettified_argparse import parseCommandLineArguments
   from manpage_data import cmdParser

Somewhere in the program, the function should be called as:

    args = parseCommandLineArguments(cmdParser)

Note that the default text formatting in the description is raw, i.e., it is
unformatted unless the formatting directive ^^f is specified.

General argparse reminders and warnings:
  1) Using nargs=1 puts the single value inside a list, default doesn't.
  2) First argument specified is the one which appears in the Usage message.
  3) The metavar kwarg sets the string for option's VALUES in Usage messages.
  4) With default values you can always assume some value is assigned.
  5) Use numargs=1 and default=[] to test whether or not, say, an int-valued
     option was selected at all (or you could check for value None).

"""

import argparse
cmdParser = argparse.ArgumentParser(
                 formatter_class=argparse.RawDescriptionHelpFormatter,
                 description=
"""
Description:

^^f
   A command-line application to crop the margins of PDF files.  Cropping the
   margins can make it easier to read the pages of a PDF document -- whether
   the document is printed or displayed on a screen -- because the font appears
   larger.  Margin-cropping is also sometimes useful when a PDF file is
   included in a document as a graphic.
   
   By default 10% of the existing margins will be retained; the rest will be
   eliminated.  There are many options which can be set, however, including the
   percentage of existing margins to retain.
   
   Here is a simple example of cropping a file named document.pdf and writing
   the cropped output-document to a file named croppedDocument.pdf:

   \a\a\apdfCropMargins document.pdf -o croppedDocument.pdf

   or

   \a\a\apython pdfCropMargins document.pdf -o croppedDocument.pdf

   The latter form is necessary if your system does not automatically recognize
   and execute Python programs.  If no destination is provided a filename will
   be automatically generated from the name of the source file (see below).

   The pdfCropMargins program works by changing the page sizes which are stored
   in the PDF file (and are interpreted by programs like Acrobat Reader).  
   Both the CropBox and the MediaBox are set to the newly-computed cropped
   size.  After this the view of the document in most programs will be the new,
   cropped view.
   
   When cropping a file not produced by the pdfCropMargins program the default
   is also to save the intersection of the MediaBox and any existing CropBox in
   the ArtBox.  This saves the "usual" view of the original document in
   programs like Acrobat Reader.  Subsequent crops of a file produced by
   pdfCropMargins do not by default alter the ArtBox.  This allows for an
   approximate "restore to original margin-sizes" option ('--restore') which
   simply copies the saved values back to the MarginBox and CropBox.  Note,
   though, that this assumes the ArtBox is unused (it is very rarely used).
   Most users should find these default settings convenient, but several
   options are available to change the default behavior.
  
   These defaults are designed to reduce the number of copies of a document
   which need to be saved.  This is especially useful if annotations,
   highlighting, etc., are to be added to the document.  Suppose a document is
   cropped and only the cropped version is saved.  Suppose also that at some
   later times the document is again cropped with pdfCropMargins and only the
   re-cropped versions are saved.  It is nevertheless still possible to recover
   at least an approximate version of the original document's margin-formatting
   from these cropped versions by using the '--restore' option.
   
   Below are several examples using more of the command-line options, each
   applied to an input file called doc.pdf.  The output filename is unspecified
   in these examples, so the program will automatically generate the filename
   (an output filename can always be explicitly provided):
^^f

     Crop doc.pdf so that all the pages are set to the same size and the
     cropping amount is uniform across all the pages (this gives a nice two-up
     appearance).  The default of retaining 10% of the existing margins is
     used.  Note carefully that '-u' only makes the amount to be cropped uniform
     for each page; if the pages do not have the same size to begin with they
     will not have the same size afterward unless the '-s' option is also used.

        pdfCropMargins -u -s doc.pdf

     Crop each page of doc.pdf individually, keeping 50% of the existing margins.

        pdfCropMargins -p 50 doc.pdf

     Crop off an absolute 12 points from each margin in doc.pdf.  Note that for
     difficult documents, such scanned books with noise or other "features"
     just inside the current margins, it can sometimes be useful to first crop
     a small absolute amount and then run the program again on the output PDF
     document.

        pdfCropMargins -a 12 doc.pdf

     Crop doc.pdf, renaming the cropped output file to doc.pdf and backing
     up the original file as backup_doc.pdf.

        pdfCropMargins -mo -pf -su "backup" doc.pdf

     Crop the margins of doc.pdf to 120% of their original size, increasing the
     margins.  Use Ghostscript to find the bounding boxes (in general this is
     usually faster if available and no rendering operations are needed).

        pdfCropMargins -p 120 -gs doc.pdf

     Crop the margins of doc.pdf ignoring the 10 largest margins on each edge
     (over the whole document).  This is especially good for noisy documents
     where all the pages have very similar margins, or when you want to ignore
     marginal annotations which only occur on a few pages.

        pdfCropMargins -m 10 doc.pdf

     Crop doc.pdf, launch the acroread viewer on the cropped output, and then
     query as to whether or not to rename the cropped file doc.pdf and back up
     the original file as doc_uncropped.pdf.

        pdfCropMargins -mo -q doc.pdf

     Crop pages 1-100 of doc.pdf, cropping all even pages uniformly and all odd
     pages uniformly.

        pdfCropMargins -g 1-100 -e doc.pdf

     Try to restore doc.pdf to its original margins, assuming it was cropped
     with pdfCropMargins previously.  Note that the output is still in
     doc_cropped.pdf.

        pdfCropMargins -r doc.pdf

^^f
   There are many different ways to use this program.  After finding a method
   which works well for a particular task or workflow pattern it is often
   convenient to make a simple shell script (batch file) which invokes the
   program with those particular options and settings.

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
   In Windows the executable would be something like "gswin32c.exe" rather than
   "gs".  The option '--gsFix' (or '-gsf') will automatically attempt to apply
   this fix, provided Ghostscript is available.  This option is helpful often
   enough that it may be worth using it regularly, just in case.
   
   All the command-line options to pdfCropMargins are described below.  The
   following definition is useful in precisely defining what several of the
   options do.  Let the delta values be the absolute reduction lengths, in
   points, which are applied to each original page to get the final cropped
   page.  There is a delta value for each margin, on each page.  In the usual
   case where all the margin sizes decrease, all the deltas are positive.  A
   delta value can, however, be negative when percentRetain>100 or when a
   negative absolute offset is used.  When a delta value is negative the
   corresponding margin size will increase.
^^f
   """,

   epilog=
"""The pdfCropMargins program is Copyright (c) 2013 by Allen Barker.  Released
under the permissive MIT license.""")

cmdParser.add_argument("pdf_input_doc", metavar="PDF_FILE", help="""

   The pathname of the PDF file to crop.  If no filename is given for the
   cropped PDF output file via the '-o' flag then a default output filename
   will be generated.  By default it is the same as the source filename except
   that the suffix ".pdf" is replaced by "_cropped.pdf", overwriting by default
   if the file already exists.  (An input filename with an alternative file
   extension or without a file extension will be handled similarly).  Use
   quotes around any file or directory name which contains a space.^^n""")

cmdParser.add_argument("-o", "--outfile", nargs=1, metavar="OUTFILE_NAME", 
      default=[], help="""

   An optional argument specifying the pathname of a file that the cropped
   output document should be written to.  By default any existing file with the
   same name will be silently overwritten.  If this option is not given the
   program will generate an output filename from the input filename (by default
   "_cropped" is appended to the input filename, keeping the same file
   extension).^^n""")

cmdParser.add_argument("-v", "--verbose", action="store_true", help="""

   Print more information about the program's actions and progress.  Without
   this switch only warning and error messages are printed to the
   screen.^^n""")

cmdParser.add_argument("-p", "--percentRetain", nargs=1, type=float, 
      metavar="PCT", default=[10.0], help="""

   Set the percent of margin space to retain in the image.  This is a
   percentage of the original margin space.  By default the percent value is
   set to 10.  Setting the percentage to 0 gives a tight bounding box.  Percent
   values greater than 100 increase the margin sizes from their original sizes,
   and negative values decrease the margins even more than a tight bounding
   box.^^n""")

cmdParser.add_argument("-pppp", "-p4", "--percentRetain4", nargs=4, type=float,
      metavar="PCT", help="""

   Set the percent of margin space to retain in the image, individually for the
   left, bottom, right, and top margins, respectively.  The four arguments
   should be percent values.^^n""")

cmdParser.add_argument("-a", "--absoluteOffset", nargs=1, type=float, 
      metavar="BP", default=[0.0], help="""

   Decrease each margin size by an absolute floating point offset value, to be
   subtracted from each margin's size.  The units are big points, bp, which is
   the unit used in PDF files.  There are 72 bp in an inch.  A single bp is
   approximately equal to a TeX point, pt (with 72.27pt in an inch).  Negative
   values are allowed; positive numbers always decrease the margin size and
   negative numbers always increase it.  Absolute offsets are always
   applied after any percentage change operations.^^n""")

cmdParser.add_argument("-aaaa", "-a4", "--absoluteOffset4", nargs=4, type=float,
      metavar = "BP", help="""

   Decrease the margin sizes individually with four absolute offset values.
   The four floating point arguments should be the left, bottom, right, and top
   offset values, respectively.  See the '--absoluteOffset' option for
   information on the units.^^n""")

cmdParser.add_argument("-u", "--uniform", action="store_true", help="""

   Crop all the pages uniformly.  This forces the magnitude of margin-cropping
   (absolute, not relative) to be the same on each page.  This option is
   applied after all the delta values have been calculated for each page,
   individually.  Then all the left-margin delta values, for each page, are set
   to the smallest left-margin delta value over every page.  The bottom, right,
   and top margins are processed similarly.  Note that this effectively adds
   some margin space (relative to the margins obtained by cropping pages
   individually) to some of the pages.  If the pages of the original document
   are all the same size then the cropped pages will again all be the same
   size.  The '--sameSize' option can also be used in combination with this
   option to force all pages to be the same size after cropping.^^n""")

cmdParser.add_argument("-m", "--uniformOrderStat", nargs=1, type=int,
      default=[], metavar="INT", help="""

   Choosing this option implies the '--uniform' option, but the smallest delta
   value over all the pages is no longer chosen.  Instead, for each margin the
   nth smallest delta value (with n numbered starting at zero) is chosen over
   all the pages.  Choosing n to be half the number of pages gives the median
   delta value.  This option is useful for cropping noisy scanned PDFs which
   have a common margin size on most of the pages, or for ignoring annotations
   which only appear in the margins of a few pages.  This option essentially
   causes the program to ignores the n largest tight-crop margins when
   computing common delta values over all the pages.  Increasing n always
   either increases the cropping amount or leaves it unchanged.  Some
   trial-and-error may be needed to choose the best number.^^n""")

cmdParser.add_argument("-mp", "--uniformOrderPercent", nargs=1, type=float, 
      default=[], metavar="INT", help="""

   This option is the same as '--uniformOrderStat' except that the order number
   n is automatically set to a given percentage of the number of pages which
   are set to be cropped (either the full number or the ones set with
   '--pages').  (This option overrides that option if both are set.) The
   argument is a float percent value; rounding is done to get the final
   order-number.  Setting the percent to 0 is equivalent to n=1, setting the
   percent to 100 is equivalent to setting n to the full number of pages, and
   setting the percent to 50 gives the median (for odd numbers of
   pages).^^n""")

cmdParser.add_argument("-s", "--samePageSize", action="store_true", help="""

   Set all the page sizes to be equal.  This option only has an effect when the
   page sizes are different.  The pages sizes are set to the size of the union
   of all the page regions, i.e., to the smallest bounding box which contains
   all the pages.  This operation is always done before any others.  The
   cropping is then done as usual, but note that any margin percentages (such
   as for '--percentRetain') are now relative to this new, possibly larger,
   page size.  The resulting pages are still cropped independently by default,
   and will not necessarily all have the same size unless '--uniform' is also
   selected to force the cropping amounts to be the same for each page.^^n""")

cmdParser.add_argument("-e", "--evenodd", action="store_true", help="""

   Crop all the odd pages uniformly, and all the even pages uniformly.  The
   largest amount of cropping that works for all the pages in each group is
   chosen.  If the '--uniform' ('-u') option is simultaneously set then the
   vertical cropping will be uniform over all the pages and only the
   horizontal cropping will differ between even and odd pages.^^n""")

cmdParser.add_argument("-g", "--pages", metavar="PAGESTR", help="""

   Apply the cropping operation only to the selected pages.  The argument
   should be a list of the usual form such as "2-4,5,9,20-30".  The
   page-numbering is assumed to start at 1.  Ordering in the argument list
   is unimportant, negative ranges are ignored, and pages falling outside the
   document are ignored.  Note that restore information is always saved for all
   the pages (in the ArtBox) unless '--noundosave' is selected.^^n""")

cmdParser.add_argument("-t", "--threshold", type=int, metavar="BYTEVAL", help="""

   Set the threshold for determining what is background space (white).  The
   value can be from 0 to 255, with 191 the default (75 percent).  This option
   may not be available for some configurations since the PDF must be
   internally rendered as an image of pixels.  In particular, it is ignored
   when '--gsBbox' is selected.  By default, any pixel value over 191 is
   considered to be background (white).^^n""")

cmdParser.add_argument("-nb", "--numBlurs", type=int, metavar="INT", help="""

   When PDF files are explicitly rendered to image files, apply a blur
   operation to the resulting images this many times.  This can be useful for
   noisy images.^^n""")

cmdParser.add_argument("-ns", "--numSmooths", type=int, metavar="INT", help="""

   When PDF files are explicitly rendered to image files, apply a smoothing
   operation to the resulting images this many times.  This can be useful for
   noisy images.^^n""")

cmdParser.add_argument("-gs", "--gsBbox", action="store_true", help="""

   Use Ghostscript to find the bounding boxes for the pages.  The alternative
   is to explicitly render the PDF pages to image files and calculate bounding
   boxes from the images.  This method tends to be much faster, but it does not
   work with scanned images.  It also does not allow for choosing the threshold
   value, applying blurs, etc.  Any resolution options are passed to the
   Ghostscript bbox device.  This option requires that Ghostscript be available
   in the PATH as "gswin32c.exe" or "gswin64c.exe" on Windows, or as "gs" on
   Linux.  When this option is set the PIL image library for Python is not
   required.^^n""")

cmdParser.add_argument("-gsr", "--gsRender", action="store_true", help="""

   Use Ghostscript to render the PDF pages to images.  By default the pdftoppm
   program will be preferred for the rendering, if it is found.  Note that this
   option has no effect if '--gsBbox' is chosen, since then no explicit
   rendering is done.^^n""")

cmdParser.add_argument("-x", "--resX", type=int, default=150,
      metavar="DPI", help="""

   The x-resolution in dots per inch to use when the image is rendered to find
   the bounding boxes.  The default is 150.  Higher values produce more precise
   bounding boxes.^^n""")

cmdParser.add_argument("-y", "--resY", type=int, default=150,
      metavar="DPI", help="""

   The y-resolution in dots per inch to use when the image is rendered to find
   the bounding boxes.  The default is 150.  Higher values produce more precise
   bounding boxes.^^n""")

cmdParser.add_argument("-b", "--boxesToSet", choices=["m","c","t","a","b"], 
      metavar="[m|c|t|a|b]", action="append", default=[], help="""

   By default the pdfCropMargins program sets both the MediaBox and the CropBox
   for each page of the cropped PDF document to the new, cropped page size.
   This default setting is usually sufficient, but this option can be used to
   select different PDF boxes to set.  The option takes one argument, which is
   the first letter (lowercase) of a type of box.  The choices are MediaBox
   (m), CropBox (c), TrimBox (t), ArtBox (a), and BleedBox (b).  This option
   overrides the default and can be repeated multiple times to set several box
   types.^^n""")

cmdParser.add_argument("-f", "--fullPageBox", choices=["m","c","t","a","b"], 
      metavar="[m|c|t|a|b]", action="append", default=[], help="""

   By default the program first (before any cropping is calculated) sets the
   MediaBox and CropBox of each page in (a copy of) the document to its
   MediaBox intersected with its CropBox.   This ensures that the cropping is
   relative to the usual document-view in programs like Acrobat Reader.   This
   essentially defines what is assumed to be the full size of pages in the
   document, and all cropping is then performed relative to that full-page
   size.  This option can be used to alternately use the MediaBox, the CropBox,
   the TrimBox, the ArtBox, or the BleedBox in defining the full-page size.
   The option takes one argument, which is the first letter (lowercase) of the
   type of box to use.  If the option is repeated then the intersection of all
   the box arguments is used.  Only one choice is allowed in combination with
   the '-gs' option since Ghostscript does its own internal rendering when
   finding bounding boxes.  The default with '-gs' is the CropBox.^^n""")

cmdParser.add_argument("-r", "--restore", action="store_true", help="""

   By default, whenever this program crops a file for the first time it saves
   the MediaBox intersected with the CropBox as the new ArtBox (since the
   ArtBox is rarely used).  The Producer metadata is checked to see if this was
   the first time.  If so, the ArtBox for each page is simply copied to the
   MediaBox and the CropBox for the page.  This restores the earlier view of
   the document, such as in Acrobat Reader (but does not completely restore the
   previous condition in cases where the MediaBox and CropBox differed or the
   ArtBox had a previous value).  Options such as '-u' which do not make sense
   in a restore operation are ignored.^^n""")

# TODO maybe later option to choose which box to save to, or none, not just
# turn off ArtBox.
cmdParser.add_argument("-A", "--noundosave", action="store_true", help="""

   Do not save any restore data in the ArtBox.  This option will need to be
   selected if the document actually uses the ArtBox for anything important
   (which is rare).  Note that the '--restore' operation will not work
   correctly for the cropped document if this option is included in the
   cropping command.  (The program does not currently check for this when doing
   a restore.)^^n""")

cmdParser.add_argument("-gsf", "--gsFix", action="store_true", help="""

   Attempt to repair the input PDF file with Ghostscript before it is read in
   with pyPdf.  This requires that Ghostscript be available as "/usr/bin/gs".
   The repaired PDF is written to a temporary file; the original PDF file is
   not modified.  The original filename is treated as usual as far as automatic
   name-generation, the '--modify-original' option, etc.^^n""")

cmdParser.add_argument("-nc", "--noclobber", action="store_true", help="""

   Never overwrite an existing file as the output file.^^n""")

cmdParser.add_argument("-pv", "--preview", metavar="PROG", help="""

   Run a PDF viewer on the cropped PDF output.  The viewer process is run in
   the background.  The viewer is launched after pdfCropMargins has finished
   all the other.  The only exception is when the '--queryModifyOriginal'
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

cmdParser.add_argument("-mo", "--modifyOriginal", action="store_true", help="""

   This option moves (renames) the original file to a backup filename and then
   moves the cropped file to the original filename.  Thus it effectively
   modifies the original file and makes a backup copy of the original,
   unmodified file.  The backup filename for the original document is always
   generated from the original filename; any prefix or suffix which would be
   added by the program to generate a filename (by default a "_cropped" suffix)
   is modified accordingly (by default to "_uncropped").  The '--usePrefix',
   '--stringUncropped', and '--stringSeparator' options can all be used to
   customize the generated backup filename.  This operation is performed last,
   so if a previous operation fails the original document will be unchanged.
   Be warned that running pdfCropMargins twice on the same source filename will
   modify the original file; the '-noclobberOriginal' option can be used to
   avoid this.^^n""")

cmdParser.add_argument("-q", "--queryModifyOriginal", action="store_true",
      help="""

   This option selects the '--modifyOriginal' option, but queries the user
   about whether to actually do the final move operation.  This works well with
   the '--preview' option: if the preview looks good you can opt to modify the
   original file (keeping a copy of the original). If you decline then the
   files are not swapped (and are just as if the '--modifyOriginal' option had
   not been set).^^n""")

cmdParser.add_argument("-nco", "--noclobberOriginal", action="store_true", 
      help="""

   If the '--modifyOriginal' option is selected, do not ever overwrite an
   existing file as the backup copy for the original file.  This essentially
   does the move operations for the '--modifyOriginal' option in noclobber
   mode, and prints a warning if it fails.  On failure the result is exactly as
   if the '--modifyOriginal' option had not been selected.  This option is
   redundant if the ordinary '--noclobber' option is also set.^^n""")

cmdParser.add_argument("-pf", "--usePrefix", action="store_true", help="""

   Prepend a prefix-string when generating default file names rather than
   appending a suffix-string.  The same string value is used, either the
   default or the one set via the '--stringCropped' or '--stringUncropped'
   option.  With the default values for the other options and no output file
   specified, this option causes the cropped output for the input file
   "document.pdf" to be written to the file named "cropped_document.pdf"
   (instead of to the default filename "document_cropped.pdf").^^n""")

cmdParser.add_argument("-sc", "--stringCropped", default="cropped",
      metavar="STR", help="""

   This option can be used to set the string which will be appended (or
   prepended) to the document filename when automatically generating the output
   filename for a cropped file.  The default value is "cropped".^^n""")

cmdParser.add_argument("-su", "--stringUncropped", default="uncropped",
      metavar="STR", help="""

   This option can be used to set the string which will be appended (or
   prepended) to the document filename when automatically generating the output
   filename for the original, uncropped file.  The default value is
   "uncropped".^^n""")

cmdParser.add_argument("-ss", "--stringSeparator", default="_", metavar="STR",
      help="""

   This option can be used to set the separator string which will be used when
   appending or prependeding string values to automatically generate filenames.
   The default value is "_".^^n""")

cmdParser.add_argument("-i", "--showImages", action="store_true", help="""

   When explicitly rendering PDF files to image files, display the inverse
   image files that are used to find the bounding boxes.  Useful for debugging
   and for choosing some of the other parameters (such as the threshold).^^n""")

cmdParser.add_argument("-pyl", "--pyPdfLocal", action="store_true", help="""

   Use a local copy of pyPdf rather than the system version.  By default the
   system version is used unless the import fails.  The local version may
   or may not be newer than the system version.^^n""")

cmdParser.add_argument("-pdl", "--pdftoppmLocal", action="store_true", help="""

   Use a locally-packaged pdftoppm executable rather than the system version.
   This option is only available on Windows machines; it is ignored otherwise.
   By default the first pdftoppm executable found in the directories in the
   PATH environment variable is used.  On Windows the program will revert to
   this option if PDF image-rendering is required and no system pdftoppm or
   Ghostscript executable can be found.  The locally-packaged pdftoppm
   executable is a few years old, but for page-cropping it only needs to get
   the margins right.^^n""")

