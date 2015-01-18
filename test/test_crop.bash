#!/bin/bash
#
# Test various options of the pdfCropMargins program on a suite of PDF files.
# Text descriptions are echoed and then visual inspection must be used to
# verify the result.
#
# Note that the PDF files themselves are written by other people and so are not
# distributed with this program.  To use this script you need to create a
# directory of PDF test files, where each file's prefix determines what options
# will be tested on the file.  At least one file should have a space in the
# filename.  Exactly one file should have the prefix "single"; that file will
# be used to test options (like naming the output file) which only need to be
# tested for one PDF file.  Set the variable TEST_PDFS_DIR below to the name of
# the directory containing these PDFs.
#
# regular_* -- regular text PDF files
# regular_arxiv* -- regular text file from archive.org with date in the margin
# scanned_* -- scanned PDF files
# corrupt_* -- files that can't be read because they're broken or wrong format (.ps)
# samesize_* -- documents with different sized pages, test making all the same, '-s'
#
# Note that on Windows the testing script is assumed to be run from Cygwin.
# The Cygwin versin of pdftoppm is currently (Jan 2015) in the poppler package.
# Poppler is also available as a Windows package.

OPTS="-v" # Extra pdfCropMargins options to pass in.
PYTHON_OS="Linux" # Can be Linux, Windows, or Cygwin; the version of Python to test.

# Locate the dir this script is in, to get path to the program and test data.
cd "$(dirname $0)"
TEST_DIR="$PWD" 
cd - 2>&1 >/dev/null

PROG_PATH="$TEST_DIR/../pdfCropMargins/pdfCropMargins"

TEST_PDFS_DIR="$TEST_DIR/../../pdf_test_files" # set this to a dir of test PDFs
cd "$TEST_PDFS_DIR"

IFS="$(printf '\n\t')" # So globbing works with spaces in filenames.

# Do some OS specific stuff.
if [ "$PYTHON_OS" == "Windows" ]; then
   PYTHON2="/cygdrive/c/Python27/python.exe"
   PYTHON3="/cygdrive/c/Python3?/python.exe" # globs to any 3?, assume just one
   PDF_READER="/cygdrive/c/Program Files*/Adobe/Reader 11.0/Reader/AcroRd32.exe"
   PDF_READER=$(echo $PDF_READER) # expand glob
   PDF_OPTIONS="/n /s"
   PROG_PATH=$(cygpath -w "$PROG_PATH") # convert argument to a Windows path
   TEST_PDFS_DIR=$(cygpath -w "$TEST_PDFS_DIR") # convert another argument
elif [ "$PYTHON_OS" == "Cygwin" ]; then
   PYTHON2="python2"
   PYTHON3="python3"
   PDF_READER="/cygdrive/c/Program Files*/Adobe/Reader 11.0/Reader/AcroRd32.exe"
   PDF_READER=$(echo $PDF_READER) # expand glob
   PDF_OPTIONS="/n /s"
elif [ "$PYTHON_OS" == "Linux" ]; then
   PYTHON2="python2"
   PYTHON3="python3"
   PDF_READER="/usr/bin/acroread"
   PDF_OPTIONS="-openInNewInstance"
else
   echo "Bad OS"
   exit 1
fi

IFS="$(printf ' \n\t')" # Restore IFS

#
# Utility functions.
#


useColors=true
# These colors are for a dark background, like the default Cygwin Bash window.
if $useColors; then
   cNotice='\e[1;32m' # light green
   cErr='\e[0;31m'   # red errors
   cCmd='\e[1;33m'  # light yellow command echo
   cInfo='\e[1;34m'  # light blue general info
   cEnd='\e[m'
   UL="\033[4m"
   BF="\033[1m"
   styleOff="\033[0m"
else
   cNotice=""; cErr=""; cCmd=""; cInfo=""; cEnd=""; UL=""; BF=""; styleOff=""
fi


indentLevel="" # global indent level, to echo indented levels

function echoInfo {
   echo -e "$indentLevel${cInfo}${1}${cEnd}"
}


function echoThenRun {
   echo -e "$indentLevel${cCmd}${@}${cEnd}"
   "$@" # run the command
}


declare -a test_pdf_files # global for array of files being tested

function get_test_pdf_files {
   # Usage: get_test_pdf_files <filePrefix>
   #
   # Gets the files with the given prefix in the test file directory, only basenames.
   # Always saves results in the global array test_pdf_files.
   readarray -t test_pdf_files < <(ls -1 $1*)
}


function afterThenBeforeDisplay {
   # Usage: afterThenBeforeDisplay <afterPDF> <beforePDF>
   # 
   # The after version is displayed first so if the displayer is opening separate
   # windows it will put the before on top of the after version.
   "$PDF_READER" $PDF_OPTIONS "$1" &
   sleep 0.5
   "$PDF_READER" $PDF_OPTIONS "$2"
   wait
   sleep 1
}


function returnToContinue {
   # Pause until user enters return.  Return value indicates if user wants to skip.
   echo -e -n "$indentLevel${cNotice}[enter <return> to continue, 'q' to skip] ${cEnd}"
   read dummy
   if [ "$dummy" == "q" ]; then
      echo -e "$indentLevel${cNotice}skipping...${cEnd}"
      return 1
   else
      return 0
   fi
}


#
# Testing functions.
#


function testRegularAndScanned {
   #   PDF_FILE              The pathname of the PDF file to crop. Use quotes
   #                         around any file or directory name which contains a
   #                         space. If no filename is given for the cropped PDF
   #                         output file via the '-o' flag then a default output
   #                         filename will be generated. By default it is the same
   #                         as the source filename except that the suffix ".pdf"
   #                         is replaced by "_cropped.pdf", overwriting by default
   #                         if the file already exists. If the input file has no
   #                         extension or has an extension other than '.pdf' or
   #                         '.PDF' then the suffix '.pdf' will be appended to the
   #                         existing (possibly-null) extension.
   #
   #   -p PCT, --percentRetain PCT
   #                         Set the percent of margin space to retain in the
   #                         image. This is a percentage of the original margin
   #                         space. By default the percent value is set to 10.
   #                         Setting the percentage to 0 gives a tight bounding
   #                         box. Percent values greater than 100 increase the
   #                         margin sizes from their original sizes, and negative
   #                         values decrease the margins even more than a tight
   #                         bounding box.
   # 
   #   -gs, --gsBbox         Use Ghostscript to find the bounding boxes for the
   #                         pages. The alternative is to explicitly render the PDF
   #                         pages to image files and calculate bounding boxes from
   #                         the images. This method tends to be much faster, but
   #                         it does not work with scanned PDF documents. It also
   #                         does not allow for choosing the threshold value,
   #                         applying blurs, etc. Any resolution options are passed
   #                         to the Ghostscript bbox device. This option requires
   #                         that Ghostscript be available in the PATH as
   #                         "gswin32c.exe" or "gswin64c.exe" on Windows, or as
   #                         "gs" on Linux. When this option is set the PIL image
   #                         library for Python is not required.
   # 
   #   -gsr, --gsRender      Use Ghostscript to render the PDF pages to images. By
   #                         default the pdftoppm program will be preferred for the
   #                         rendering, if it is found. Note that this option has
   #                         no effect if '--gsBbox' is chosen, since then no
   #                         explicit rendering is done.
   # 
   #   -u, --uniform         Crop all the pages uniformly. This forces the
   #                         magnitude of margin-cropping (absolute, not relative)
   #                         to be the same on each page. This option is applied
   #                         after all the delta values have been calculated for
   #                         each page, individually. Then all the left-margin
   #                         delta values, for each page, are set to the smallest
   #                         left-margin delta value over every page. The bottom,
   #                         right, and top margins are processed similarly. Note
   #                         that this effectively adds some margin space (relative
   #                         to the margins obtained by cropping pages
   #                         individually) to some of the pages. If the pages of
   #                         the original document are all the same size then the
   #                         cropped pages will again all be the same size. The '--
   #                         sameSize' option can also be used in combination with
   #                         this option to force all pages to be the same size
   #                         after cropping.
   #
   #   -s, --samePageSize    Set all the page sizes to be equal. This option only
   #                         has an effect when the page sizes are different. The
   #                         pages sizes are set to the size of the union of all
   #                         the page regions, i.e., to the smallest bounding box
   #                         which contains all the pages. This operation is always
   #                         done before any others (except '--absolutePreCrop').
   #                         The cropping is then done as usual, but note that any
   #                         margin percentages (such as for '--percentRetain') are
   #                         now relative to this new, possibly larger, page size.
   #                         The resulting pages are still cropped independently by
   #                         default, and will not necessarily all have the same
   #                         size unless '--uniform' is also selected to force the
   #                         cropping amounts to be the same for each page.
   # 

   get_test_pdf_files regular
   
   echoInfo
   echoInfo "Formatting each regular file and each scanned file for"
   echoInfo "rendering.  The cropping percent will increase through several values."
   returnToContinue || return
 
   if [ "$page_crop_info_program" == "pdftoppm" ]; then
      info_prog="" # default
   elif [ "$page_crop_info_program" == "ghostscript_rendering" ]; then
      info_prog="-gsr"
   elif [ "$page_crop_info_program" == "ghostscript_bbox" ]; then
      info_prog="-gs"
   fi

   if [ "$crop_style_option" == "default" ]; then
      style="" # default
      echoInfo "Each page should be cropped by its individual margins (default)."
   elif [ "$crop_style_option" == "uniform_samesize" ]; then
      style="-u -s"
      echoInfo "All pages should be the same size and uniformly cropped."
   fi

   for i in "${test_pdf_files[@]}"
   do
      indentLevel="         "
      
      echoInfo
      echoInfo "Running for this regular file: $i"
      returnToContinue || continue

      indentLevel="            "
      echoInfo
      echoInfo "First, -10%, which should cut into the text."
      returnToContinue || continue
      echoThenRun $python_version "$PROG_PATH" $OPTS $info_prog $style -p -10 -pf "$i"
      afterThenBeforeDisplay "cropped_$i" "$i"
      rm cropped_*

      echoInfo
      echoInfo "Now, 0%, which should be a tight-fitting crop around the text."
      returnToContinue || continue
      echoThenRun $python_version "$PROG_PATH" $OPTS $info_prog $style -p 0 -pf "$i"
      afterThenBeforeDisplay "cropped_$i" "$i"
      rm cropped_*

      echoInfo
      echoInfo "Now, 10%, which should be a good default value."
      returnToContinue || continue
      echoThenRun $python_version "$PROG_PATH" $OPTS $info_prog $style -p 10 -pf "$i"
      afterThenBeforeDisplay "cropped_$i" "$i"
      rm cropped_*

      echoInfo
      echoInfo "Now, 50% which should leave half."
      returnToContinue || continue
      echoThenRun $python_version "$PROG_PATH" $OPTS $info_prog $style -p 50 -pf "$i"
      afterThenBeforeDisplay "cropped_$i" "$i"
      rm cropped_*

      echoInfo
      echoInfo "Now, 100%, which should do almost nothing."
      returnToContinue || continue
      echoThenRun $python_version "$PROG_PATH" $OPTS $info_prog $style -p 100 -pf "$i"
      afterThenBeforeDisplay "cropped_$i" "$i"
      rm cropped_*

      echoInfo
      echoInfo "Now, 200%, which should double the margins."
      returnToContinue || continue
      echoThenRun $python_version "$PROG_PATH" $OPTS $info_prog $style -p 200 -pf "$i"
      afterThenBeforeDisplay "cropped_$i" "$i"
      rm cropped_*

   done
   indentLevel="      "

   if [ "$page_crop_info_program" != "ghostscript_bbox" ]; then
      get_test_pdf_files scanned
      echoInfo
      echoInfo "Testing a 10% crop on all files with 'scanned' prefix."
      echoInfo "Note that noisy scans may not work well; this is just a test."
      returnToContinue || return

      for i in "${test_pdf_files[@]}"
      do
         indentLevel="         "
         echoInfo
         echoInfo "Running for this regular file: $i"
         returnToContinue || continue

         echoThenRun $python_version "$PROG_PATH" $OPTS $info_prog $style -pf "$i"
         afterThenBeforeDisplay "cropped_$i" "$i"
         rm cropped_*
      done
      indentLevel="      "
   fi
}


function testSamePageSize {
   # Another test of the -s option, not combined with -u.
   get_test_pdf_files samesize
   echoInfo
   echoInfo "Testing only setting pages to the same size.  The percent."
   echoInfo "retained is 100%, so it should just make pages the same size."
   returnToContinue || return

   for i in "${test_pdf_files[@]}"
   do
      echoInfo
      echoInfo "Running for this file: $i"
      returnToContinue || continue

      echoThenRun $python_version "$PROG_PATH" $OPTS -s -p 100 -pf "$i"
      afterThenBeforeDisplay "cropped_$i" "$i"
      rm cropped_*
   done
}


function testOutputFilename {
   #   -o OUTFILE_NAME, --outfile OUTFILE_NAME
   #                         An optional argument specifying the pathname of a file
   #                         that the cropped output document should be written to.
   #                         By default any existing file with the same name will
   #                         be silently overwritten. If this option is not given
   #                         the program will generate an output filename from the
   #                         input filename. (By default "_cropped" is appended to
   #                         the input filename before the file extension. If the
   #                         extension is not '.pdf' or '.PDF' then '.pdf' is
   #                         appended to the extension).
   
   echoInfo
   echoInfo "Testing renaming of output file on the single PDF file.  The cropped"
   echoInfo "file should appear, named 'myname.pdf'."
   returnToContinue || return
   echoThenRun $python_version "$PROG_PATH" $OPTS -o myname.pdf "$single"
   afterThenBeforeDisplay "myname.pdf" "$single"
   rm myname.pdf
}


function testHelp {
   #   -h, --help            Show this help message and exit.

   echoInfo
   echoInfo "Testing the help message.  Look over and see if it looks OK."
   returnToContinue || return
   echoThenRun $python_version "$PROG_PATH" $OPTS -h | more
}

# These options haven't yet been added to automated testing.

   #   -v, --verbose         Print more information about the program's actions and
   #                         progress. Without this switch only warning and error
   #                         messages are printed to the screen.
   # 
   #   -p4 PCT PCT PCT PCT, -pppp PCT PCT PCT PCT, --percentRetain4 PCT PCT PCT PCT
   #                         Set the percent of margin space to retain in the
   #                         image, individually for the left, bottom, right, and
   #                         top margins, respectively. The four arguments should
   #                         be percent values.
   # 
   #   -a BP, --absoluteOffset BP
   #                         Decrease each margin size by an absolute floating
   #                         point offset value, to be subtracted from each
   #                         margin's size. The units are big points, bp, which is
   #                         the unit used in PDF files. There are 72 bp in an
   #                         inch. A single bp is approximately equal to a TeX
   #                         point, pt (with 72.27pt in an inch). Negative values
   #                         are allowed; positive numbers always decrease the
   #                         margin size and negative numbers always increase it.
   #                         Absolute offsets are always applied after any
   #                         percentage change operations.
   # 
   #   -a4 BP BP BP BP, -aaaa BP BP BP BP, --absoluteOffset4 BP BP BP BP
   #                         Decrease the margin sizes individually with four
   #                         absolute offset values. The four floating point
   #                         arguments should be the left, bottom, right, and top
   #                         offset values, respectively. See the '--
   #                         absoluteOffset' option for information on the
   #                         units.
   # 
   #   -ap BP, --absolutePreCrop BP
   #                         This option is like '--absoluteOffset' except that the
   #                         changes are applied before any bounding box
   #                         calculations (or any other operations). The argument
   #                         is the same, in units of bp. This is essentially
   #                         equivalent to first cropping the document retaining
   #                         100% of the margins but applying an absolute offset
   #                         and then doing any other operations on that pre-
   #                         cropped file.
   # 
   #   -ap4 BP BP BP BP, --absolutePreCrop4 BP BP BP BP
   #                         This is the same as '--absolutePreCrop' except that
   #                         four separate arguments can be given. The four
   #                         floating point arguments should be the left, bottom,
   #                         right, and top absolute pre-crop values,
   #                         respectively.
   # 
   #   -m INT, --uniformOrderStat INT
   #                         Choosing this option implies the '--uniform' option,
   #                         but the smallest delta value over all the pages is no
   #                         longer chosen. Instead, for each margin the nth
   #                         smallest delta value (with n numbered starting at
   #                         zero) is chosen over all the pages. Choosing n to be
   #                         half the number of pages gives the median delta value.
   #                         This option is useful for cropping noisy scanned PDFs
   #                         which have a common margin size on most of the pages,
   #                         or for ignoring annotations which only appear in the
   #                         margins of a few pages. This option essentially causes
   #                         the program to ignores the n largest tight-crop
   #                         margins when computing common delta values over all
   #                         the pages. Increasing n always either increases the
   #                         cropping amount or leaves it unchanged. Some trial-
   #                         and-error may be needed to choose the best number.
   # 
   #   -mp INT, --uniformOrderPercent INT
   #                         This option is the same as '--uniformOrderStat' except
   #                         that the order number n is automatically set to a
   #                         given percentage of the number of pages which are set
   #                         to be cropped (either the full number or the ones set
   #                         with '--pages'). (This option overrides that option if
   #                         both are set.) The argument is a float percent value;
   #                         rounding is done to get the final order-number.
   #                         Setting the percent to 0 is equivalent to n=1, setting
   #                         the percent to 100 is equivalent to setting n to the
   #                         full number of pages, and setting the percent to 50
   #                         gives the median (for odd numbers of pages).
   # 
   #   -e, --evenodd         Crop all the odd pages uniformly, and all the even
   #                         pages uniformly. The largest amount of cropping that
   #                         works for all the pages in each group is chosen. If
   #                         the '--uniform' ('-u') option is simultaneously set
   #                         then the vertical cropping will be uniform over all
   #                         the pages and only the horizontal cropping will differ
   #                         between even and odd pages.
   # 
   #   -g PAGESTR, --pages PAGESTR
   #                         Apply the cropping operation only to the selected
   #                         pages. The argument should be a list of the usual form
   #                         such as "2-4,5,9,20-30". The page-numbering is assumed
   #                         to start at 1. Ordering in the argument list is
   #                         unimportant, negative ranges are ignored, and pages
   #                         falling outside the document are ignored. Note that
   #                         restore information is always saved for all the pages
   #                         (in the ArtBox) unless '--noundosave' is selected.
   # 
   #   -t BYTEVAL, --threshold BYTEVAL
   #                         Set the threshold for determining what is background
   #                         space (white). The value can be from 0 to 255, with
   #                         191 the default (75 percent). This option may not be
   #                         available for some configurations since the PDF must
   #                         be internally rendered as an image of pixels. In
   #                         particular, it is ignored when '--gsBbox' is selected.
   #                         By default, any pixel value over 191 is considered to
   #                         be background (white).
   # 
   #   -nb INT, --numBlurs INT
   #                         When PDF files are explicitly rendered to image files,
   #                         apply a blur operation to the resulting images this
   #                         many times. This can be useful for noisy images.
   # 
   #   -ns INT, --numSmooths INT
   #                         When PDF files are explicitly rendered to image files,
   #                         apply a smoothing operation to the resulting images
   #                         this many times. This can be useful for noisy
   #                         images.
   # 
   #   -x DPI, --resX DPI    The x-resolution in dots per inch to use when the
   #                         image is rendered to find the bounding boxes. The
   #                         default is 150. Higher values produce more precise
   #                         bounding boxes.
   # 
   #   -y DPI, --resY DPI    The y-resolution in dots per inch to use when the
   #                         image is rendered to find the bounding boxes. The
   #                         default is 150. Higher values produce more precise
   #                         bounding boxes.
   # 
   #   -b [m|c|t|a|b], --boxesToSet [m|c|t|a|b]
   #                         By default the pdfCropMargins program sets both the
   #                         MediaBox and the CropBox for each page of the cropped
   #                         PDF document to the new, cropped page size. This
   #                         default setting is usually sufficient, but this option
   #                         can be used to select different PDF boxes to set. The
   #                         option takes one argument, which is the first letter
   #                         (lowercase) of a type of box. The choices are MediaBox
   #                         (m), CropBox (c), TrimBox (t), ArtBox (a), and
   #                         BleedBox (b). This option overrides the default and
   #                         can be repeated multiple times to set several box
   #                         types.
   # 
   #   -f [m|c|t|a|b], --fullPageBox [m|c|t|a|b]
   #                         By default the program first (before any cropping is
   #                         calculated) sets the MediaBox and CropBox of each page
   #                         in (a copy of) the document to its MediaBox
   #                         intersected with its CropBox. This ensures that the
   #                         cropping is relative to the usual document-view in
   #                         programs like Acrobat Reader. This essentially defines
   #                         what is assumed to be the full size of pages in the
   #                         document, and all cropping is then performed relative
   #                         to that full-page size. This option can be used to
   #                         alternately use the MediaBox, the CropBox, the
   #                         TrimBox, the ArtBox, or the BleedBox in defining the
   #                         full-page size. The option takes one argument, which
   #                         is the first letter (lowercase) of the type of box to
   #                         use. If the option is repeated then the intersection
   #                         of all the box arguments is used. Only one choice is
   #                         allowed in combination with the '-gs' option since
   #                         Ghostscript does its own internal rendering when
   #                         finding bounding boxes. The default with '-gs' is the
   #                         CropBox.
   # 
   #   -r, --restore         By default, whenever this program crops a file for the
   #                         first time it saves the MediaBox intersected with the
   #                         CropBox as the new ArtBox (since the ArtBox is rarely
   #                         used). The Producer metadata is checked to see if this
   #                         was the first time. If so, the ArtBox for each page is
   #                         simply copied to the MediaBox and the CropBox for the
   #                         page. This restores the earlier view of the document,
   #                         such as in Acrobat Reader (but does not completely
   #                         restore the previous condition in cases where the
   #                         MediaBox and CropBox differed or the ArtBox had a
   #                         previous value). Options such as '-u' which do not
   #                         make sense in a restore operation are ignored. Note
   #                         that as far as default filenames the operation is
   #                         treated as just another crop operation (the default-
   #                         generated output filename still has a "_cropped.pdf"
   #                         suffix). The '--modifyOriginal' option (or its query
   #                         variant) can be used with this option.
   # 
   #   -A, --noundosave      Do not save any restore data in the ArtBox. This
   #                         option will need to be selected if the document
   #                         actually uses the ArtBox for anything important (which
   #                         is rare). Note that the '--restore' operation will not
   #                         work correctly for the cropped document if this option
   #                         is included in the cropping command. (The program does
   #                         not currently check for this when doing a restore.)
   # 
   #   -gsf, --gsFix         Attempt to repair the input PDF file with Ghostscript
   #                         before it is read-in with pyPdf. This requires that
   #                         Ghostscript be available. (See the general description
   #                         text above for the actual command that is run.) This
   #                         can also be used to automatically convert some
   #                         PostScript files (.ps) to PDF for cropping. The
   #                         repaired PDF is written to a temporary file; the
   #                         original PDF file is not modified. The original
   #                         filename is treated as usual as far as automatic name-
   #                         generation, the '--modify-original' option, and so
   #                         forth. This option is often helpful if the program
   #                         hangs or raises an error due to a corrupted PDF file.
   #                         Note that when re-cropping a file already cropped by
   #                         pdfCropMargins this option is probably not be
   #                         necessary, and if it is used in a re-crop (at least
   #                         with current versions of Ghostscript) it will reset
   #                         the Producer metadata which the pdfCropMargins program
   #                         uses to tell if the file was already cropped by the
   #                         program (the '--restore' option will then restore to
   #                         the previous cropping, not the original cropping). So
   #                         this option is not recommended as something to use by
   #                         default unless you encounter many corrupted PDF files
   #                         and do not need to restore back to the original
   #                         margins.
   # 
   #   -nc, --noclobber      Never overwrite an existing file as the output
   #                         file.
   # 
   #   -pv PROG, --preview PROG
   #                         Run a PDF viewer on the cropped PDF output. The viewer
   #                         process is run in the background. The viewer is
   #                         launched after pdfCropMargins has finished all the
   #                         other. The only exception is when the '--
   #                         queryModifyOriginal' option is also selected. In that
   #                         case the viewer is launched before the query so that
   #                         the user can look at the output before deciding
   #                         whether or not to modify the original. (Note that
   #                         answering 'y' will then move the file out from under
   #                         the running viewer; close and re-open the file before
   #                         adding annotations, highlighting, etc.) The single
   #                         argument should be the path of the executable file or
   #                         script to run the chosen viewer. The viewer is assumed
   #                         to take exactly one argument, a PDF filename. For
   #                         example, on Linux the Acrobat Reader could be chosen
   #                         with /usr/bin/acroread or, if it is in the PATH,
   #                         simply acroread. A shell script or batch file wrapper
   #                         can be used to set any additional options for the
   #                         viewer.
   # 
   #   -mo, --modifyOriginal
   #                         This option moves (renames) the original file to a
   #                         backup filename and then moves the cropped file to the
   #                         original filename. Thus it effectively modifies the
   #                         original file and makes a backup copy of the original,
   #                         unmodified file. The backup filename for the original
   #                         document is always generated from the original
   #                         filename; any prefix or suffix which would be added by
   #                         the program to generate a filename (by default a
   #                         "_cropped" suffix) is modified accordingly (by default
   #                         to "_uncropped"). The '--usePrefix', '--
   #                         stringUncropped', and '--stringSeparator' options can
   #                         all be used to customize the generated backup
   #                         filename. This operation is performed last, so if a
   #                         previous operation fails the original document will be
   #                         unchanged. Be warned that running pdfCropMargins twice
   #                         on the same source filename will modify the original
   #                         file; the '-noclobberOriginal' option can be used to
   #                         avoid this.
   # 
   #   -q, --queryModifyOriginal
   #                         This option selects the '--modifyOriginal' option, but
   #                         queries the user about whether to actually do the
   #                         final move operation. This works well with the '--
   #                         preview' option: if the preview looks good you can opt
   #                         to modify the original file (keeping a copy of the
   #                         original). If you decline then the files are not
   #                         swapped (and are just as if the '--modifyOriginal'
   #                         option had not been set).
   # 
   #   -nco, --noclobberOriginal
   #                         If the '--modifyOriginal' option is selected, do not
   #                         ever overwrite an existing file as the backup copy for
   #                         the original file. This essentially does the move
   #                         operations for the '--modifyOriginal' option in
   #                         noclobber mode, and prints a warning if it fails. On
   #                         failure the result is exactly as if the '--
   #                         modifyOriginal' option had not been selected. This
   #                         option is redundant if the ordinary '--noclobber'
   #                         option is also set.
   # 
   #   -pf, --usePrefix      Prepend a prefix-string when generating default file
   #                         names rather than appending a suffix-string. The same
   #                         string value is used, either the default or the one
   #                         set via the '--stringCropped' or '--stringUncropped'
   #                         option. With the default values for the other options
   #                         and no output file specified, this option causes the
   #                         cropped output for the input file "document.pdf" to be
   #                         written to the file named "cropped_document.pdf"
   #                         (instead of to the default filename
   #                         "document_cropped.pdf").
   # 
   #   -sc STR, --stringCropped STR
   #                         This option can be used to set the string which will
   #                         be appended (or prepended) to the document filename
   #                         when automatically generating the output filename for
   #                         a cropped file. The default value is "cropped".
   # 
   #   -su STR, --stringUncropped STR
   #                         This option can be used to set the string which will
   #                         be appended (or prepended) to the document filename
   #                         when automatically generating the output filename for
   #                         the original, uncropped file. The default value is
   #                         "uncropped".
   # 
   #   -ss STR, --stringSeparator STR
   #                         This option can be used to set the separator string
   #                         which will be used when appending or prependeding
   #                         string values to automatically generate filenames. The
   #                         default value is "_".
   # 
   #   -pw PASSWD, --password PASSWD
   #                         Specify a password to be used to decrypt an encrypted
   #                         PDF file. Note that decrypting with an empty password
   #                         is always tried, so this option is only needed for
   #                         non-empty passwords. The resulting cropped file will
   #                         not be encrypted, so use caution if important data is
   #                         involved.
   # 
   #   -i, --showImages      When explicitly rendering PDF files to image files,
   #                         display the inverse image files that are used to find
   #                         the bounding boxes. Useful for debugging and for
   #                         choosing some of the other parameters (such as the
   #                         threshold).
   # 
   #   -pyl, --pyPdfLocal    Use a local copy of pyPdf rather than the system
   #                         version. By default the system version is used unless
   #                         the import fails. The local version may or may not be
   #                         newer than the system version.
   # 
   #   -pdl, --pdftoppmLocal
   #                         Use a locally-packaged pdftoppm executable rather than
   #                         the system version. This option is only available on
   #                         Windows machines; it is ignored otherwise. By default
   #                         the first pdftoppm executable found in the directories
   #                         in the PATH environment variable is used. On Windows
   #                         the program will revert to this option if PDF image-
   #                         rendering is required and no system pdftoppm or
   #                         Ghostscript executable can be found. The locally-
   #                         packaged pdftoppm executable is a few years old, but
   #                         for page-cropping it only needs to get the margins
   #                         right.


##
## Begin the actual script.
##

echoInfo "Running tests on the files in directory:"
echoInfo "   $TEST_PDFS_DIR"
# Get the single file and save its name to a variable to avoid having to repeat.
get_test_pdf_files single
single="${test_pdf_files[0]}"
echoInfo "The file which will be used for single-file tests is:"
echoInfo "   $single"
echoInfo
echoInfo "For visual verification, this program will first display the cropped"
echoInfo "version, and then the uncropped version (which should appear on top"
echoInfo "or in the newest tab."

for python_version in $PYTHON2 $PYTHON3
do
   indentLevel=""
   echoInfo
   echoInfo "#######################################################"
   echoInfo "#######################################################"
   echoInfo "Running all tests using $python_version"
   echoInfo "#######################################################"
   echoInfo "#######################################################"
   returnToContinue || continue

   for page_crop_info_program in pdftoppm ghostscript_bbox ghostscript_rendering
   do
      indentLevel="   "
      echoInfo
      echoInfo "#######################################################"
      echoInfo "Running the tests based on cropping using this program"
      echoInfo "to render or get cropping info: $page_crop_info_program"
      echoInfo "#######################################################"
      returnToContinue || continue

      for crop_style_option in default uniform_samesize
      do
         indentLevel="      "
         echoInfo
         echoInfo "Running cropping tests using the cropping option:"
         echoInfo "   $crop_style_option"
         returnToContinue || continue
         testRegularAndScanned
      done
      indentLevel="   "
   done
   
   testSamePageSize
   testOutputFilename
   testHelp
done  
indentLevel=""

echoInfo
echoInfo "Finished the automated tests."

