==============
pdfCropMargins
==============

The pdfCropMargins program is a command-line application to automatically crop
the margins of PDF files.  Cropping the margins can make it easier to read the
pages of a PDF document -- whether the document is printed or displayed on a
screen -- because the display fonts are larger.  This program is similar to the
Perl script pdfcrop except with many more options.

Features
========

- Automatically detects the margins and can crop a given percentage of them.
- Can crop all the pages to the same size to give a uniform appearance (such as
  in two-up).
- Works on Linux, Windows, Cygwin, and OS X/Darwin.
- Has an optional graphical user interface (GUI) for interactive cropping.
- Renders and analyzes page images to find the bounding boxes, which allows it
  to deal with noisy scanned PDFs.
- A rudimentary 'undo' capability is implemented by default. 
- Can crop pages uniformly based on the nth smallest crop values, which helps
  with noisy images or documents where a few pages have unwanted markings in
  their margins.
- Can automatically run a document previewer on the output file.
- The format of automatically-generated output-file names is easily
  modifiable.
- Preserves document catalog information such as outlines if possible.
- Crops rotated pages according to their appearance in the document viewer.
- Can deal with at least simple cases of password-encrypted files.
- Works with either MuPDF, the pdftoppm program, or the Ghostscript program to
  find the bounding boxes.
- Can automatically apply a Ghostscript repair operation to attempt to fix
  corrupt PDF files.

This GIF shows the optional GUI, before and after cropping a document:

.. image:: https://user-images.githubusercontent.com/1791335/63413846-9c9e3400-c3c8-11e9-90f5-6e429ae2d74b.gif
    :width: 450px
    :align: center
    :alt: [GIF of pdfCropMargins]

What's New
==========

See the `CHANGELOG
<https://github.com/abarker/pdfCropMargins/blob/master/CHANGELOG.rst>`_ for
recent changes and new features.

* Version 2.1.2 has new options to center text on the pages after cropping.
  They are ``--centerText``,  ``--centerTextHoriz``, ``--centerTextVert``,  and
  ``--centeringStrict``.

* New in version 2.0.1, the option ``--setSamePageSize`` (``-ssp``) allows a
  custom page box size to be passed in rather than having the program calculate
  the largest containing box size.

Installing 
==========

The easiest way to install the pdfCropMargins program is by using pip.

The basic features work out of the box, some of the options require either the
external program pdftoppm or Ghostscript.  For information on installing those
programs on Linux and Windows, see: `Installing pdftoppm and/or Ghostscript
<https://github.com/abarker/pdfCropMargins/tree/master/doc/installing_pdftoppm_and_ghostscript.rst>`_
.

Linux/Ubuntu
------------

If you are installing via pip with the ``--user`` option be sure
``$HOME/.local/bin`` is in your system ``PATH``.  (To install system-wide
without ``--user`` the ``pip3`` command below would need to be run with
``sudo``.)

.. code-block:: sh

   sudo apt install python3-tk
   sudo apt install ghostscript poppler-utils # Optional, for ghostscript and pdftoppm.
   pip3 install pdfCropMargins --user --upgrade

**Troubleshooting:** If you have problems with the install of PyMuPDF, the
first thing to try is to upgrade your version of the pip program and then
retry:

.. code-block:: sh

   pip3 install pip --upgrade --user

If you still get an error "Failed building wheel for pymupdf" with the GUI
install you can try forcing a binary install of PyMuPDF:

.. code-block:: sh

   pip3 install pdfCropMargins --user --upgrade --only-binary pymupdf

Windows
-------

The install command is:

.. code-block:: sh

   pip install pdfCropMargins --upgrade

The ``pip`` program should be automatically installed along with Python.  If
you cannot find the pip executable you can usually run it like this:

.. code-block:: sh

   python -m pip <arguments-to-pip>

Note that on some Windows installs the executable for Python is ``py`` rather
than ``python``.

In order for the command ``pdfcropmargins`` to work from the command line the
Python ``bin`` directory must be on the Windows ``Path``.  The system-wide
Python ``bin`` directory should already be on the path if you checked the box
to modify ``Path`` when you installed Python; otherwise it should be added.
(Note that if you install with the ``--user`` option to pip then you need to be
sure that the *local* Python ``bin`` directory is in the Windows ``Path``.)

Running
=======

The program can be run 1) from the command line, 2) from the command line with
a GUI, 3) from a Python program, or 3) from the source repo.

Running from the command line
-----------------------------

After installation via pip the program can be run with either the command
``pdfcropmargins`` or the command ``pdf-crop-margins``.  For example:

.. code-block:: sh

   pdfcropmargins -v -s -u your-file.pdf

That command prints verbose output, forces all pages to be the same size
(``-s``) and then crops each page by the same amount (``-u``) for a uniform
appearance, retaining the default of 10% of the margins.  To run the
same command with the GUI for fine-tuning, use:

.. code-block:: sh

   pdfcropmargins -v -s -u -gui your-file.pdf

For help and to see the many command-line options that are available, run:

.. code-block:: sh

   pdfcropmargins -h | more

The full output of that command is also listed below, at the bottom of this
page.  On Windows you may need to explicitly put the Python distribution's
``Scripts`` directory into your environment ``PATH`` in order to avoid having
to use the full pathname.

Running with the GUI
--------------------

To run the GUI, assuming that version of pdfCropMargins has been installed,
just pass the ``-gui`` flag in addition to any other flags.  The program is
still a command-line application, and still respects all the flags, but the GUI
lets you fine-tune the values of some of the command-line arguments such as the
percent to crop, etc.  The output filenames, etc., are all the same as for the
command-line version.  Options modifiable from the GUI are initially set to any
values passed in on the command line.

The graphical display shows the effect of each crop when you hit the 'Crop'
button.  Multiple cropping calls for the same document tend to be faster
because the PDF pages usually only need to be rendered to images one time.

Python interface
----------------

The program can also be called from a user's Python program (when the
``pdfCropMargins`` package is discoverable in the Python path).  Just import
the ``crop`` function and then call it with a list containing the usual
command-line arguments as separate items.  For example:
  
.. code-block:: python

   from pdfCropMargins import crop
   crop(["-p", "20", "-u", "-s", "paper1.pdf"])
   crop(["-p", "0", "-gui", "paper2.pdf"])

Any necessary exception handling should be performed by the calling code.  The
code may call ``sys.exit``, so checking for ``SystemExit`` or ``BaseException`` may
be required.

The ``crop`` function always returns four values, some of which may be set to
``None``:

* the output file path,

* the exit code,

* the text written to standard input,

* the text written to standard output.

If the keyword argument ``string_io`` is set true (the default is false) then
standard output and standard error streams are temporarily redirected to
capture any output text as strings, which are returned as the final two
arguments.  Otherwise those values are set to ``None``.  The keyword argument
``quiet`` implies the ``string_io`` argument, but does not echo anything to the
terminal while the ``crop`` function runs.

An example usage:

.. code-block:: python

   output_doc_pathname, exit_code, stdout_str, stderr_str = crop(
                            ["-p4", "0", "10", "0", "10", "paper2.pdf"],
                            string_io=True, quiet=False)

Running from the source distribution
------------------------------------

The pdfCropMargins program can be run directly from the source code directory
tree, provided the dependencies are installed.  Just clone the repo and run the
program ``pdfCropMargins.py`` located in the ``bin`` directory.

To pip install the program and its dependencies from the cloned repo rather
than from PyPI just go to the root of the source directory and run ``pip install .``
(As usual, for code development use the ``-e`` option to make the code
editable.)

Getting good crops
------------------

* To diagnose unexpected crops, look at the pages with the smallest delta values,
  as indicated in the verbose (``-v``) output or at the bottom of the GUI.
  This tells you the page with the smallest crop amount for a margin.

* Running without the ``-u`` or ``-s`` options will crop each page separately,
  so you can see which pages might be causing problems (such as pages with
  noise near the borders or margin text).

* To get cropped pages all the same size be sure to use both ``-s`` to first
  make pages the same size and ``-u`` to crop each page by the same amount.

* Sometimes a small pre-crop is needed (``-ap`` or ``-ap4``) to get past small,
  unwanted markings near the edges of pages.

Documentation
=============

.. In vim use this to get output:
       :read !pdf-crop-margins -h

To see the documentation, run::

   pdf-crop-margins -h | more

The output of that command follows::

   Usage: pdfcropmargins [-h] [-o OUTFILE_PATH_OR_DIR] [-v] [-gui] [-p PCT]
                         [-p4 PCT PCT PCT PCT] [-pt] [-a BP] [-a4 BP BP BP BP]
                         [-cs] [-csm4 BP BP BP BP] [-ap BP] [-ap4 BP BP BP BP]
                         [-u] [-m INT] [-m4 INT INT INT INT] [-mp INT] [-s]
                         [-ms INT] [-ssp FLOAT FLOAT FLOAT FLOAT] [-e]
                         [-g PAGESTR] [-c [d|m|p|gr|gb|o]] [-gs] [-gsr]
                         [-t BYTEVAL] [-nb INT] [-ns INT] [-x DPI] [-y DPI]
                         [-sr STR] [-gf INT] [-b [m|c|t|a|b]] [-f [m|c|t|a|b]]
                         [-r] [-A] [-gsf] [-nc] [-pv PROG] [-mo] [-q] [-nco]
                         [-pf] [-sc STR] [-su STR] [-ss STR] [-pw PASSWD] [-pc]
                         [-khc] [-kvc] [-spr FLOAT:FLOAT]
                         [-prw FLOAT FLOAT FLOAT FLOAT] [-ct] [-ch] [-cv] [-cst]
                         [-i] [-pdl] [-gsp PATH] [-ppp PATH] [--version]
                         [-wcdf FILEPATH]
                         PDF_FILE [PDF_FILE ...]

   Description:

        A command-line application to crop the margins of PDF files. Cropping
        the margins can make it easier to read the pages of a PDF document --
        whether the document is printed or displayed on a screen -- because the
        display fonts are larger. Margin-cropping is also sometimes useful when
        a PDF file is included in a document as a graphic.

        By default 10% of the existing margins will be retained; the rest will
        be eliminated. There are many options which can be set, however,
        including the percentage of existing margins to retain.

        Here is a simple example of cropping a file named document.pdf and
        writing the cropped output-document to a file named
        croppedDocument.pdf:

           pdfcropmargins document.pdf -o croppedDocument.pdf

        The alias 'pdf-crop-margins' can also be used to launch the program in
        place of 'pdfcropmargins'. If no destination is provided a filename
        will be automatically generated from the name of the source file (see
        below).

        The pdfCropMargins program works by changing the page sizes which are
        stored in the PDF file (and are interpreted by programs like Acrobat
        Reader). Both the CropBox and the MediaBox are set to the newly-
        computed cropped size. After this the view of the document in most
        programs will be the new, cropped view.

        In order to reduce the number of copies of a document which must be
        saved, a basic '--restore' option is provided. When cropping a file not
        produced by the pdfCropMargins program the default is to save the
        intersections of the MediaBox and any existing CropBox for each page as
        XML metadata. This saves the "usual" view of the original document in
        programs like Acrobat Reader. Subsequent crops of a file produced by
        pdfCropMargins do not by default alter the saved data. The restore
        option simply copies the saved values back to the MediaBox and CropBox.
        (Old versions of the program saved to the ArtBox; if these are cropped
        again the data is migrated to XML metadata.)

        Below are several examples using more of the command-line options, each
        applied to an input file called doc.pdf. The output filename is
        unspecified in most of these examples, so the program will
        automatically generate the filename (or an output filename can always
        be explicitly provided with '-o'):

        1) Crop doc.pdf so that all the pages are set to the same size and the
        cropping amount is uniform across all the pages (this gives a nice two-up
        appearance).  The default of retaining 10% of the existing margins is
        used.  Note carefully that '-u' only makes the amount to be cropped uniform
        for each page; if the pages do not have the same size to begin with they
        will not have the same size afterward unless the '-s' option is also used.

           pdfcropmargins -u -s doc.pdf

        2) Crop each page of doc.pdf individually (i.e., not uniformly), keeping 50%
        of the existing margins.

           pdfcropmargins -p 50 doc.pdf

        3) Crop doc.pdf uniformly, keeping 50% of the left margin, 20% of the bottom
        margin, 40% of the right margin, and 10% of the top margin.

           pdfcropmargins -u -p4 50 20 40 10 doc.pdf

        4) Crop doc.pdf retaining 20% of the margins, and then reduce the right page
        margins only by an absolute 12 points.

           pdfcropmargins -p 20 -a4 0 0 12 0 doc.pdf

        5) Add a constant 5bp around the bare bounding boxes on all pages (note the
        negative value passed to the `-a` option, which adds space rather than
        removing it).

           pdfcropmargins -p 0 -a -5 doc.pdf

        6) Pre-crop the document by 5bp on each side before computing the bounding
        boxes.  Then crop retaining 50% of the computed margins.  This can be
        useful for difficult documents such as scanned books with page-edge noise
        or other "features" inside the current margins.

           pdfcropmargins -ap 5 -p 50 doc.pdf

        7) Crop doc.pdf, re-naming the cropped output file to doc.pdf and backing
        up the original file in a file named backup_doc.pdf.

           pdfcropmargins -mo -pf -su "backup" doc.pdf

        8) Crop the margins of doc.pdf to 120% of their original size, increasing
        the margins.  Use Ghostscript to find the bounding boxes without explicit
        rendering by pdfCropMargins.

           pdfcropmargins -p 120 -c gb doc.pdf

        9) Crop the margins of doc.pdf ignoring the 10 largest margins on each edge
        (over the whole document).  This is especially good for noisy documents
        where all the pages have very similar margins, or when you want to ignore
        marginal annotations which only occur on a few pages.

           pdfcropmargins -m 10 doc.pdf

        10) Crop doc.pdf, launch the acroread viewer on the cropped output, and then
        query as to whether or not to rename the cropped file doc.pdf and back up
        the original file as doc_uncropped.pdf.

           pdfcropmargins -mo -q doc.pdf

        11) Crop pages 1-100 of doc.pdf, cropping all even pages uniformly and all odd
        pages uniformly.

           pdfcropmargins -g 1-100 -e doc.pdf

        12) Try to restore doc.pdf to its original margins, assuming it was cropped
        with pdfCropMargins previously.  Note that the default output filename is
        still named doc_cropped.pdf, even though it is the recovered file.  Use the
        '-mo' option to modify doc.pdf and backup the previous version.

           pdfcropmargins -r doc.pdf

        There are many different ways to use this program. After finding a
        method which works well for a particular task or workflow pattern it is
        often convenient to make a simple shell script (batch file) which
        invokes the program with those particular options and settings. Simple
        template scripts for Bash and Windows are packaged with the program, in
        the bin directory. The program can also be called from a user's Python
        program (when discoverable in the Python path) by using code such as

           from pdfCropMargins import crop
           crop(["-p", "20", "-u", "-s", "paper.pdf"])

        When printing a document with closely-cropped pages it may be necessary
        to use options such as "Fit to Printable Area". It may also be
        necessary to fine-tune the size of the retained margins if the edges of
        the text are being cut off.

        Sometimes a PDF file is corrupted or non-standard to the point where
        the routines used by this program raise an error and exit. In that case
        it can sometimes help to repair the PDF file before attempting to crop
        it. If it is readable by Ghostscript then the following command will
        often repair it sufficiently:

           gs -o repaired.pdf -sDEVICE=pdfwrite -dPDFSETTINGS=/prepress corrupted.pdf

        This command can also be used to convert some PostScript (.ps) files to
        PDF. The option '--gsFix' (or '-gsf') will automatically attempt to
        apply this fix, provided Ghostscript is available. See the description
        of that option for more information.

        The pdfCropMargins program handles rotated pages (such as pages in
        landscape mode versus portrait mode) as follows. All rotated pages are
        un-rotated as soon as they are read in. All the cropping is then
        calculated. Finally, as the crops are applied to the pages, the
        rotation is re-applied. This may give unexpected results in documents
        which mix pages at different rotations, especially with the '--uniform'
        or '--samePageSize' options. For rotated pages the arguments of all the
        options which take four arguments, one for each margin, are shifted so
        the left, bottom, right, and top margins correspond to the screen
        appearance (regardless of any internal rotation).

        All the command-line options to pdfCropMargins are described below. The
        following definition is useful in precisely defining what several of
        the options do. The "delta values" are the absolute reduction lengths,
        in points, which are applied to each original page to get the final
        cropped page. There is a delta value for each margin, on each page. In
        the usual case where all the margin sizes decrease, all the deltas are
        positive. A delta value can, however, be negative (e.g., when
        percentRetain > 100 or when a negative absolute offset is used). When a
        delta value is negative the corresponding margin size will increase.
      

   Positional arguments:

     PDF_FILE     The pathname of the PDF file to crop. Use quotes around any
                  file or directory name which contains a space. If no filename
                  is given for the cropped PDF output file via the '-o' flag then
                  a default output filename will be generated. By default it is
                  the same as the source filename except that the suffix ".pdf"
                  is replaced by "_cropped.pdf", overwriting by default if the
                  file already exists. The file will be written to the working
                  directory at the time when the program was run. If the input
                  file has no extension or has an extension other than '.pdf' or
                  '.PDF' then the suffix '.pdf' will be appended to the existing
                  (possibly-null) extension. Globbing of wildcards and shell
                  variable expansions are performed on the path.


   Optional arguments:

     -h, --help   Show this help message and exit.

     -o OUTFILE_PATH_OR_DIR, --outfile OUTFILE_PATH_OR_DIR
                  An optional argument specifying the directory or file path that
                  the cropped output document should be written to. If this
                  option is not given the program will generate an output
                  filename from the input filename and write to the current
                  working directory. By default the string "_cropped" is appended
                  to the input filename just before the file extension. (If the
                  extension is not '.pdf' or '.PDF' then '.pdf' is also appended
                  to the extension.) The options '--usePrefix', '--stringCropped'
                  and '--stringSeparator' can be used to customize the generated
                  filenames. By default any existing file with the same name will
                  be silently overwritten; this can be avoided with the '--
                  noclobber' option. Globbing of wildcards and shell variable
                  expansions are performed on the directory path but not on the
                  filename part.

     -v, --verbose
                  Print more information about the program's actions and
                  progress. Without this switch only warning and error messages
                  are printed to the screen.

     -gui, --gui  Run the graphical user interface. This mode allows you to
                  interactively preview and test different cropping options
                  without having to recalculate the bounding boxes each time
                  (which can be slow). All the usual command-line options to the
                  program are still respected. Clicking the 'Crop' button in the
                  GUI crops with the current settings, writing out a cropped PDF
                  file to the same filename that the command-line version would
                  write to. Note that successive changes to the margins in the
                  GUI are not cumulative: settings are always applied to the
                  original document as it was passed in to the program. The
                  'Original' button reverts the display back to that original
                  version.

     -p PCT, --percentRetain PCT
                  Set the percent of margin space to retain in the image. This is
                  a percentage of the original margin space. By default the
                  percent value is set to 10. Setting the percentage to 0 gives a
                  tight bounding box. Percent values greater than 100 increase
                  the margin sizes from their original sizes, and negative values
                  decrease the margins even more than a tight bounding box.

     -p4 PCT PCT PCT PCT, -pppp PCT PCT PCT PCT, --percentRetain4 PCT PCT PCT PCT
                  Set the percent of margin space to retain in the image,
                  individually for the left, bottom, right, and top margins,
                  respectively. The four arguments should be percent values.
                  Percent values greater than 100 increase the margin sizes from
                  their original sizes, and negative values decrease the margins
                  even more than a tight bounding box.

     -pt, --percentText
                  Normally the percentage values passed to '--percentRetain' or '
                  --percentRetain4' define the percentage of existing margins to
                  retain. This flag alters the interpretation of those percent
                  values. The margins are instead set to the given percentage of
                  the text width or height. The left and right margins are set to
                  a percentage of the bounding box width and the bottom and top
                  margins are set to a percentage of the bounding box height.

     -a BP, --absoluteOffset BP
                  Decrease each margin size by an absolute floating point offset
                  value, to be subtracted from each margin's size after the
                  'percentRetain' option is applied. The units are big points,
                  bp, which is the unit used in PDF files. There are 72 bp in an
                  inch. A single bp is approximately equal to a TeX point, pt
                  (with 72.27pt in an inch). Negative values are allowed;
                  positive numbers always decrease the margin size and negative
                  numbers always increase it. Absolute offsets are always applied
                  after any percentage change operations.

     -a4 BP BP BP BP, -aaaa BP BP BP BP, --absoluteOffset4 BP BP BP BP
                  Decrease the margin sizes individually with four absolute
                  offset values. The four floating point arguments should be the
                  left, bottom, right, and top offset values, respectively. See
                  the '--absoluteOffset' option for information on the units.

     -cs, --cropSafe
                  Guarantee that all crops are safe in the sense that no crop
                  ever goes beyond the tight bounding box on any margin. This
                  does not apply to pre-crops using the '--absolutePreCrop'
                  option. It also does not apply to any margins on pages where
                  that margin is ignored due to the '--uniformOrderStat' or '--
                  uniformOrderStat4' option. The latter effect works well with
                  uniform cropping in the GUI: the value of 'uniformOrderStat'
                  can be incremented for the margin with the minimum delta value
                  (as seen by clicking that button) if no useful text would be
                  cropped out. The '--cropSafeMin' option allows for modifying
                  the minimum margin value, adding to the bounding box.

     -csm4 BP BP BP BP, --cropSafeMin4 BP BP BP BP
                  The '--cropSafe' option will not perform any crops that cut
                  into the bounding box. This option modifies the behavior of
                  that option (assuming that `--cropSafe` is also selected).
                  Instead of stopping at the bounding box, it will not crop past
                  the bounding box plus the corresponding margin values passed
                  in. This applies to all margins. The option takes four floats,
                  in units of big points, for the left, bottom, right, and top
                  margins, respectively. Negative values are allowed and allow
                  some of the bounding box to be cropped.

     -ap BP, --absolutePreCrop BP
                  This option is like '--absoluteOffset' except that it is
                  applied before any bounding box calculations (or any other
                  operations). The argument is the same, in units of bp. All
                  successive operations are then relative to this pre-crop box,
                  considered to be the full-page box. Note that since this
                  absolute crop is applied before any bounding boxes are computed
                  it is relative to the original full-page boxes of the document
                  (unlike 'absoluteOffset', which is a crop relative to the
                  newly-cropped margin after 'percentRetain' is applied). As a
                  consequence, the number of points may need to be larger than
                  what would work for 'absoluteOffset'. This option can be used
                  to ignore text and markings out at the edge of the margins by
                  cropping it out before the bounding boxes are calculated.

     -ap4 BP BP BP BP, --absolutePreCrop4 BP BP BP BP
                  This is the same as '--absolutePreCrop' except that four
                  separate arguments can be given. The four floating point
                  arguments should be the left, bottom, right, and top absolute
                  pre-crop values, respectively.

     -u, --uniform
                  Crop all the pages uniformly. This forces the magnitude of
                  margin-cropping (absolute, not relative) to be the same on each
                  page. This option is applied after all the delta values have
                  been calculated for each page, individually. Then all the left-
                  margin delta values, for each page, are set to the smallest
                  left-margin delta value over every page. The bottom, right, and
                  top margins are processed similarly. Note that this effectively
                  adds some margin space (relative to the margins obtained by
                  cropping pages individually) to some of the pages. If the pages
                  of the original document are all the same size then the cropped
                  pages will again all be the same size. The '--samePageSize'
                  option can be used in combination with this option to force all
                  pages to be the same size after cropping.

     -m INT, --uniformOrderStat INT
                  Choosing this option implies the '--uniform' option, but the
                  smallest delta value over all the pages is no longer chosen.
                  Instead, for each margin the nth smallest delta value (with n
                  numbered starting at zero) is chosen over all the pages. The
                  argument is the integer n, for example '-m 4'. Choosing n to be
                  half the number of pages gives the median delta value. This
                  option is useful for cropping noisy scanned PDFs which have a
                  common margin size on most of the pages, or for ignoring
                  annotations which only appear in the margins of a few pages.
                  This option essentially causes the program to ignores the n
                  largest tight-crop margins when computing common delta values
                  over all the pages. Increasing n always either increases the
                  cropping amount or leaves it unchanged. Some trial-and-error
                  may be needed to choose the best number. Using '-m 1' tends to
                  work well with arXiv papers (which have a date in the margin of
                  the first page).

     -m4 INT INT INT INT, -mmmm INT INT INT INT, --uniformOrderStat4 INT INT INT INT
                  This option is the same as '--uniformOrderStat' (or '-m')
                  except that separate values are specified for each margin
                  individually. The margins are ordered as left, bottom, right,
                  and top.

     -mp INT, --uniformOrderPercent INT
                  This option is the same as '--uniformOrderStat' except that the
                  order number n is automatically set to a given percentage of
                  the number of pages which are set to be cropped (either the
                  full number or the ones set with '--pages'). This option
                  overrides '--uniformOrderStat' if both are set. The argument is
                  a float percent value; rounding is done to get the final order-
                  number. Setting the percent to 0 is equivalent to n=1, setting
                  the percent to 100 is equivalent to setting n to the full
                  number of pages, and setting the percent to 50 gives the median
                  (for odd numbers of pages).

     -s, --samePageSize
                  Set all the page sizes to be equal. This option only has an
                  effect when the page sizes are different. The pages sizes are
                  set to the size of the union of all the page regions, i.e., to
                  the smallest bounding box which contains all the pages. This
                  operation is always done before any others (except '--
                  absolutePreCrop'). The cropping is then done as usual, but note
                  that any margin percentages (such as for '--percentRetain') are
                  now relative to this new, possibly larger, page size. The
                  resulting pages are still cropped independently by default, and
                  will not necessarily all have the same size unless '--uniform'
                  is also selected to force the cropping amounts to be the same
                  for each page. If pages are selected with '--pages' then this
                  option is only applied to those selected pages.

     -ms INT, --samePageSizeOrderStat INT
                  Choosing this option implies the '--samePageSize' option, but
                  the calculations for each edge of the smallest bounding box
                  ignore the largest (or smallest for left and bottom edges) n
                  values. The argument is the nonnegative number n. Each edge is
                  calculated independently. This is an order statistic for
                  selecting the uniform size to make the pages. Note that this
                  will cut off parts of some pages if n>0.

     -ssp FLOAT FLOAT FLOAT FLOAT, --setSamePageSize FLOAT FLOAT FLOAT FLOAT
                  This option is like the '--samePageSize' option except the page
                  size to set is passed in as four floating point arguments
                  rather than being calculated. The numbers should represent the
                  left, bottom, right, and top margin values, respectively. The
                  origin is at the lower left. The numbers should be in points
                  and are absolute, i.e., not relative to any current margins.
                  The `--samePageSize` option will override this option if it is
                  set.

     -e, --evenodd
                  Crop all the odd pages uniformly, and all the even pages
                  uniformly. The largest amount of cropping that works for all
                  the pages in each group is chosen. If the '--uniform' ('-u')
                  option is simultaneously set then the vertical cropping will be
                  uniform over all the pages and only the horizontal cropping
                  will differ between even and odd pages. See also the '--
                  percentText' option which can be used for a similar effect.

     -g PAGESTR, -pg PAGESTR, --pages PAGESTR
                  Apply the cropping operation only to the selected pages. The
                  argument should be a list of the usual form such as
                  "2-4,5,9,20-30". The page-numbering is assumed to start at 1.
                  Ordering in the argument list is unimportant, negative ranges
                  are ignored, and pages falling outside the document are
                  ignored. Note that restore information is always saved for all
                  the pages (in the ArtBox) unless '--noundosave' is selected.

     -c [d|m|p|gr|gb|o], --calcbb [d|m|p|gr|gb|o]
                  Choose the method to calculate bounding boxes (or to render the
                  PDF pages in order to calculate the boxes). The default option
                  'd' will currently choose the MuPDF rendering option. The
                  options to force a particular method are MuPDF ('m'), pdftoppm
                  ('p'), or Ghostscript ('gr') for rendering, or direct
                  Ghostscript bounding-box calculation ('gb'). For pdftoppm or
                  Ghostscript options the corresponding program must be installed
                  and locatable (see the path-setting options below if the
                  default locator fails). Only the explicit rendering methods
                  will work for scanned pages (see '--gsBbox'). Choosing 'o'
                  reverts to the old default behavior of first looking for
                  pdftoppm and then looking for Ghostscript for rendering.

     -gs, --gsBbox
                  This option is maintained for backward compatibility; using '-c
                  gb' is now preferred. Use Ghostscript to directly find the
                  bounding boxes for the pages, with no explict rendering of the
                  pages. (The default is to explicitly render the PDF pages to
                  image files and calculate bounding boxes from the images.) This
                  method tends to be much faster, but it does not work with
                  scanned PDF documents. It also does not allow for choosing the
                  threshold value, applying blurs, etc. Any resolution options
                  are passed to the Ghostscript bbox device. This option requires
                  that Ghostscript be available in the PATH as "gswin32c.exe" or
                  "gswin64c.exe" on Windows, or as "gs" on Linux. When this
                  option is set the Pillow image library for Python is not
                  required.

     -gsr, --gsRender
                  This is maintained for backward compatibility; using '-c gr' is
                  now preferred. Use Ghostscript to render the PDF pages to
                  images. By default the pdftoppm program will be preferred for
                  the rendering, if it is found. Note that this option has no
                  effect if '--gsBbox' is chosen, since then no explicit
                  rendering is done.

     -t BYTEVAL, --threshold BYTEVAL
                  Set the threshold for determining what is background space
                  (white). The value can be from 0 to 255, with 191 the default
                  (75 percent). This option may not be available for some
                  configurations since the PDF must be internally rendered as an
                  image of pixels. In particular, it is ignored when '--gsBbox'
                  is selected. Any pixel value over the threshold is considered
                  to be background (white), and any value below it is considered
                  to be text (black). Lowering the value should tend to make the
                  bounding boxes smaller. The threshold may need to be lowered,
                  for example, for scanned images with greyish backgrounds. For
                  pages with dark backgrounds and light text a negative threshold
                  value can be used. In that case the absolute value is used as
                  the threshold but the test is reversed to consider pixel values
                  greater than or equal to the threshold to be background.

     -nb INT, --numBlurs INT
                  When PDF files are explicitly rendered to image files, apply a
                  blur operation to the resulting images this many times. This
                  can be useful for noisy images.

     -ns INT, --numSmooths INT
                  When PDF files are explicitly rendered to image files, apply a
                  smoothing operation to the resulting images this many times.
                  This can be useful for noisy images.

     -x DPI, --resX DPI
                  The x-resolution in dots per inch to use when the image is
                  rendered to find the bounding boxes. The default is 150. Higher
                  values produce more precise bounding boxes but require more
                  time and memory.

     -y DPI, --resY DPI
                  The y-resolution in dots per inch to use when the image is
                  rendered to find the bounding boxes. The default is 150. Higher
                  values produce more precise bounding boxes but require more
                  time and memory.

     -sr STR, --screenRes STR
                  Pass in an X-windows style geometry string for the GUI to use
                  as the fullscreen resolution and for the upper-left placement
                  of the window. This is mainly for when the screen-size
                  detection algorithm fails for a particular system. For example,
                  with a screen of size "1024x720" that string should be used
                  with the option. To also place the window at (0,0) the string
                  would be "1024x728+0+0". See also the '--guiFontSize' option
                  which can be used to decrease the overall size of the GUI
                  window.

     -gf INT, --guiFontSize INT
                  Choose the GUI font size. Making this smaller than the default
                  of 11 can also make the GUI smaller if it does not fit on a
                  smaller monitor.

     -b [m|c|t|a|b], --boxesToSet [m|c|t|a|b]
                  By default the pdfCropMargins program sets the MediaBox for
                  each page of the cropped PDF document to the new, cropped page
                  size. This default setting is usually sufficient, but this
                  option can be used to select different PDF boxes to set. The
                  option takes one argument, which is the first letter
                  (lowercase) of a type of box. The choices are MediaBox (m),
                  CropBox (c), TrimBox (t), ArtBox (a), and BleedBox (b). This
                  option overrides the default and can be repeated multiple times
                  to set several box types. Note that the program now uses
                  PyMuPDF to set the boxes, and it will refuse to set any non-
                  MediaBox boxes unless they are fully contained in the MediaBox.
                  In that case a warning will be issued and the box will not be
                  set.

     -f [m|c|t|a|b], --fullPageBox [m|c|t|a|b]
                  By default the program first (before any cropping is
                  calculated) sets the MediaBox of each page in (a copy of) the
                  document to the intersection of its previous MediaBox and
                  CropBox. This ensures that the cropping is relative to the
                  usual document-view in programs like Acrobat Reader. This
                  essentially defines what is assumed to be the full size of
                  pages in the document, and all cropping is then performed
                  relative to that full-page size. This option can be used to
                  alternately use the MediaBox, the CropBox, the TrimBox, the
                  ArtBox, or the BleedBox in defining the full-page size. The
                  option takes one argument, which is the first letter
                  (lowercase) of the type of box to use. If the option is
                  repeated then the intersection of all the box arguments is
                  used. Only one choice is allowed in combination with the '-gs'
                  option since Ghostscript does its own internal rendering when
                  finding bounding boxes. The default with '-gs' is the
                  CropBox.

     -r, --restore
                  This is a simple undo operation which essentially undoes all
                  the crops ever made by pdfCropMargins and returns to the
                  original margins (provided no other program modified the saved
                  XML data for the pdfCropMargins key). By default, whenever this
                  program crops a file for the first time it saves the MediaBox
                  intersected with the CropBox for each page as XML metadata. The
                  XML metadata is is checked to see if there is any existing
                  restore data. If so, the saved metadata for each page is simply
                  copied to the MediaBox and the CropBox for the page. This
                  restores the earlier view of the document, such as in Acrobat
                  Reader (but does not completely restore the previous condition
                  in cases where the MediaBox and CropBox differed). Any options
                  such as '-u', '-p', and '-a' which do not make sense in a
                  restore operation are ignored. Note that as far as default
                  filenames the operation is treated as just another crop
                  operation (the default-generated output filename still has a
                  "_cropped.pdf" suffix). The '--modifyOriginal' option (or its
                  query variant) can be used with this option. Saving restore
                  data as XML metadata can be disabled by using the '--
                  noundosave' option.

     -A, --noundosave
                  Do not save any restore data as XML metadata. Note that the '--
                  restore' operation will not work correctly for the cropped
                  document later if this option is included in the cropping
                  command.

     -gsf, --gsFix
                  Attempt to repair the input PDF file with Ghostscript before it
                  is read-in. This requires that Ghostscript be available. (See
                  the general description text above for the actual command that
                  is run.) This can also be used to automatically convert some
                  PostScript files (.ps) to PDF for cropping. The repaired PDF is
                  written to a temporary file; the original PDF file is not
                  modified. The original filename is treated as usual as far as
                  automatic name-generation, the '--modify-original' option, and
                  so forth. This option is often helpful if the program hangs or
                  raises an error due to a corrupted PDF file. Note that when re-
                  cropping a file already cropped by pdfCropMargins this option
                  is probably not necessary, and if it is used in a re-crop (at
                  least with current versions of Ghostscript) it will reset the
                  Producer metadata which the pdfCropMargins program uses to tell
                  if the file was already cropped by the program (so the '--
                  restore' option will not work in combination with this option).
                  This option is not recommended as something to use by default
                  unless you encounter many corrupted PDF files and do not need
                  to restore back to the original margins.

     -nc, --noclobber
                  Never overwrite an existing file with the cropped output
                  file.

     -pv PROG, --preview PROG
                  Run a PDF viewer on the cropped PDF output. The viewer process
                  is run in the background. The viewer is launched after
                  pdfCropMargins has finished all the other options. The only
                  exception is when the '--queryModifyOriginal' option is also
                  selected. In that case the viewer is launched before the query
                  so that the user can look at the output before deciding whether
                  or not to modify the original. (Note that answering 'y' will
                  then move the file out from under the running viewer; close and
                  re-open the file before adding annotations, highlighting, etc.)
                  The single argument should be the path of the executable file
                  or script to run the chosen viewer. The viewer is assumed to
                  take exactly one argument, a PDF filename. For example, on
                  Linux the Acrobat Reader could be chosen with /usr/bin/acroread
                  or, if it is in the PATH, simply acroread. A shell script or
                  batch file wrapper can be used to set any additional options
                  for the viewer.

     -mo, --modifyOriginal
                  This option moves (renames) the original document file to a
                  backup filename and then moves the cropped file to the original
                  document's filename (and directory path). Thus it effectively
                  crops the original document file in-place and makes a backup
                  copy of the original file in the output directory. The backup
                  filename for the original document is always generated from the
                  original filename; any prefix or suffix which would be added by
                  the program to generate a filename (by default a "_cropped"
                  suffix) is modified accordingly (by default to "_uncropped").
                  The '--usePrefix', '--stringUncropped', and '--stringSeparator'
                  options can all be used to customize the generated backup
                  filename. If an output path is specified via the '--outfile'
                  ('-o') option then the backup document is written to that
                  directory (the same directory the cropped file was first
                  written to). This operation is performed last, so if a previous
                  operation fails the original document will be unchanged. Be
                  warned that running pdfCropMargins twice on the same source
                  path with this option will modify the backed-up original file;
                  the '--noclobberOriginal' option can be used to avoid this.

     -q, --queryModifyOriginal
                  This option selects the '--modifyOriginal' option, but queries
                  the user about whether to actually do the final move operation.
                  This works well with the '--preview' or '--gui' options: if the
                  preview looks good you can opt to modify the original file
                  (keeping a copy of the original). If you decline then the files
                  are not swapped (and are just as if the '--modifyOriginal'
                  option had not been set).

     -nco, --noclobberOriginal
                  If the '--modifyOriginal' option is selected, do not ever
                  overwrite an existing file as the backup copy for the original
                  file. This essentially does the move operations for the '--
                  modifyOriginal' option in noclobber mode, and prints a warning
                  if it fails. On failure the result is exactly as if the '--
                  modifyOriginal' option had not been selected. This option is
                  redundant if the ordinary '--noclobber' option is also set.

     -pf, --usePrefix
                  Prepend a prefix-string when generating default file names
                  rather than appending a suffix-string. The same string value is
                  used, either the default or the one set via the '--
                  stringCropped' or '--stringUncropped' option. With the default
                  values for the other options and no output file specified, this
                  option causes the cropped output for the input file
                  "document.pdf" to be written to the file named
                  "cropped_document.pdf" (instead of to the default filename
                  "document_cropped.pdf").

     -sc STR, --stringCropped STR
                  This option can be used to set the string which will be
                  appended (or prepended) to the document filename when
                  automatically generating the output filename for a cropped
                  file. The default value is "cropped".

     -su STR, --stringUncropped STR
                  This option can be used to set the string which will be
                  appended (or prepended) to the document filename when
                  automatically generating the output filename for the original,
                  uncropped file. The default value is "uncropped".

     -ss STR, --stringSeparator STR
                  This option can be used to set the separator string which will
                  be used when appending or prepending string values to
                  automatically generate filenames. The default value is "_".

     -pw PASSWD, --password PASSWD
                  Specify a password to be used to decrypt an encrypted PDF file.
                  Note that decrypting with an empty password is always tried, so
                  this option is only needed for non-empty passwords. The
                  resulting cropped file will not be encrypted, so use caution if
                  important data is involved.

     -pc, --prevCropped
                  Test whether or not the document was previously cropped with
                  the pdfCropMargins program. If so, exit with exit code 0. If
                  not, exit with exit code 1. This option is intended mainly for
                  scripting, for example to only crop documents that have not
                  been previously cropped. Requires a document filename option.
                  No other options are honored when this option is selected
                  except '--gsFix', '--version', and '--help'.

     -khc, --keepHorizCenter
                  This option keeps the horizontal center point of a PDF fixed.
                  The usual crops are calculated, but for each page the left and
                  right delta values are both set to the smallest of the two
                  values (so the cropping amount is the same on each side). This
                  option does not apply to pre-crops.

     -kvc, --keepVertCenter
                  This option keeps the vertical center point of a PDF fixed. The
                  usual crops are calculated, but for each page the upper and
                  lower delta values are both set to the smallest of the two
                  values (so the cropping amount is the same on the top and
                  bottom). This option does not apply to pre-crops.

     -spr FLOAT:FLOAT, --setPageRatios FLOAT:FLOAT
                  Force all the cropped page ratios to equal the given ratio. All
                  crops are calculated and applied as usual, but either the left
                  and right margins will be increased equally or else the top and
                  bottom margins will be increased equally in order to make the
                  ratio of width to height equal the set value. Margins are only
                  ever increased. The format for the ratio is either a string
                  width-to-height ratio such as '4.5:3' or else a floating point
                  number like '0.75' which is the width divided by the height.
                  This option can be useful in some PDF viewers.

     -prw FLOAT FLOAT FLOAT FLOAT, --pageRatioWeights FLOAT FLOAT FLOAT FLOAT
                  This option weights any whitespace added by the '--
                  setPageRatios' argument. It takes four weight arguments, one
                  per margin. The four floating point arguments should be the
                  left, bottom, right, and top weights, respectively. The weights
                  determine what proportion of the total height(width) increase
                  necessary to achieve the target page ratio is added to the
                  corresponding margin. All weights must be greater than zero.

     -ct, --centerText
                  Center the text horizontally and vertically after cropping. The
                  crop for each page is adjusted so that the tight bounding box
                  is centered in the page (if possible). If an order statistic
                  method like '--uniformOrderStat' is applied then, for ignored
                  edges, the bounding box edge that was actually used to
                  calculate the crop values is used. If the '--centeringStrict'
                  flag is set then each page will be centered regardless of any
                  order statistic calculation.

     -ch, --centerTextHoriz
                  This is the same as '--centerText' except pages are only
                  centered horizontally.

     -cv, --centerTextVert
                  This is the same as '--centerText' except pages are only
                  centered vertically.

     -cst, --centeringStrict
                  This flag modifies the behavior of bounding-box-centering
                  options like '--centerText'. Normally pages ignored for order
                  statistic operations like '--uniformOrderStat' are also ignored
                  for centering and the page actually used for cropping is used
                  for centering. This option forces strict centering of each
                  page.

     -i, --showImages
                  When explicitly rendering PDF files to image files, display the
                  inverse image files that are used to find the bounding boxes.
                  Useful for debugging and for choosing some of the other
                  parameters (such as the threshold). This option requires a
                  default external viewer program selected by the Pillow image
                  manipulation package (xv on Unix, and usually Paint on
                  Windows).

     -pdl, --pdftoppmLocal
                  This option is deprecated. Use a locally-packaged pdftoppm
                  executable rather than the system version. This option is only
                  available on Windows machines; it is ignored otherwise. By
                  default the first pdftoppm executable found in the directories
                  in the PATH environment variable is used. On Windows the
                  program will revert to this option if PDF image-rendering is
                  required, PyMuPDF is not installed, and no system pdftoppm or
                  Ghostscript executable can be found.

     -gsp PATH, --ghostscriptPath PATH
                  Pass in a pathname to the ghostscript executable that the
                  program should use. No globbing is done. Useful when the
                  program is in a nonstandard location.

     -ppp PATH, --pdftoppmPath PATH
                  Pass in a pathname to the pdftoppm executable that the program
                  should use. No globbing is done. Useful when the program is in
                  a nonstandard location.

     --version    Return the pdfCropMargins version number and exit immediately.
                  All other options are ignored.

     -wcdf FILEPATH, --writeCropDataToFile FILEPATH
                  Write out the calculated list of crops to the file with the
                  file pathname that is passed in and exit. Mostly used for
                  automated testing and debugging.


   The pdfCropMargins program is Copyright (c) 2014 by Allen Barker.
   Released under the GNU GPL license, version 3 or later.
