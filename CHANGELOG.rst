.. :changelog:

History
=======

1.1.[0-1] (2022-12-07)
----------------------

* Upgraded to Python 3.6 minimum requirement with pyupgrade.

* The GUI dependencies are now part of the standard install (although the program
  will still run without them if the GUI is not required).

* Dependency versions updated for security and functionality changes.

* The alias ``pdfcropmargins`` can now be used instead of ``pdf-crop-margins``
  from the command line.

1.0.9 (2022-07-14)
------------------

Bug fixes:

* Bug in decryption error for non-encrypted file.

1.0.8 (2022-06-20)
------------------

New features:

* Finalized and documented the return values and keyword arguments to the
  ``crop`` function in the Python interface.  Now returns the output filename,
  the exit code, and optionally the stdout and stdin text.

1.0.7 (2022-06-20)
------------------

Bug fixes:

* Changed PyMuPDF method names to match new convention (they removed deprecated
  older camelcase names with 1.20.0).

* Updated PyMuPDF requirement to 1.20.0.

1.0.6 (2022-06-15)
------------------

Bug fixes:

* Import of `PdfReadError` now tries the `errors` module and then the `utils` module.

* Updated some dependency minimum versions for security reasons.


1.0.5 (2021-03-08)
------------------

Bug fixes:

* Workaround for a bug related to PyMuPDF attribute naming.

1.0.4 (2021-03-01)
------------------

New features:

* The output file path specified by the ``--outfile`` (``-o``) option can now
  be a directory.  In that case all output files will be written to that
  directory using the default-generated names.  The ``--modifyOriginal``
  (``--mo``) option will also use the directory part of any output path
  provided for the backup of the original.

Bug fixes:

* The ``--modifyOriginal`` (``-mo``) option now modifies the original file
  even if it is in a different directory than the output file.

* A file permission/access problem in Windows that occurred with some option
  combinations was fixed.

1.0.3 (2021-02-14)
------------------

Bug fixes:

* Minor workaround for a naming issue introduced in newer versions of PyMuPDF.

1.0.2 (2020-11-15)
------------------

Changes:

* PDFs are now opened with ``strict=FALSE`` in PyPDF2 ``PdfFileReader``
  objects.  This will attempt to repair some PDF errors in documents that
  previously caused read errors.

1.0.1 (2020-11-12)
------------------

Changes:

* Globs are now applied in Python to file arguments on non-Windows systems (in
  addition to Windows systems).  This way they work in the Python interface as
  well as from a shell like Bash that expands them before passing them.  In the
  unlikely case that a glob character is in an actual PDF file name it might
  need to be quoted twice (once escaped).  Shell variables are now also
  expanded in Python if detected.

Bug fixes:

* The program no longer attempts to glob user-supplied output filenames, which
  was issuing an unnecessary warning (due to a recent change).

1.0.0 (2020-10-23)
------------------

New features:

* The MuPDF program can now be used to calculate the crops.  This is done
  in-memory, and tends to be fast.  It requires PyMuPDF to be installed in
  Python -- it is already installed with the GUI option, or can be
  user-installed enable the option without the GUI dependencies. This is now
  the default method of cropping if PyMuPDF is detected and importable.  To
  force using this method, use the ``--calcbb m`` or ``-c m`` option.

* The preferred way to select the method of calculating bounding boxes has
  changed.  Use ``--calcbb`` or the shortcut ``-c`` with one of 'm' (MuPDF),
  'p' (pdftoppm), 'gr' (Ghostscript rendering), or 'gb' (direct Ghostscript
  bounding box calculation) as the argument.  The default selection sequence is
  'd'.  Passing 'o' reverts to the older (before MuPDF) default sequence.

* The default rendering resolution is now 72 dpi instead of 150 dpi.
  Resolution can still be set with the ``-x`` and ``-y`` options.

* A new option flag ``--percentText`` which changes the interpretation of
  the percentage values passed to ``--percentRetain`` and ``--percentRetain4``.
  With this flag the left and right margins are set to a percentage of the
  bounding box width and the top and bottom margins are set to a percentage
  of the bounding box height.

Bug fixes:

* Remove a debug print statement of bounding boxes that was left after a 0.2.10
  negative-threshold fix.

* Fixed bug in ``--version`` argument.

* Improved sizing of GUI windows.

0.2.1[23456] (2020-09-22)
-------------------------

Bug fixes:

* Fixed a recently-introduced bug in GUI events when running Python2.

* Drop Pillow requirement for Python 2 (versions newer than 7.0.0 not supported
  and have security vulnerabilities).  Add a warning on importing old Pillow
  versions they might have installed or choose to install.  Also include
  ``typing`` backport requirement for Python 2 versions of PySimpleGUI27.

* Import ``readline`` so prompts are sent to stdout instead of stderr, except
  on Windows Python which doesn't support readline.

0.2.11 (2020-09-12)
-------------------

New features:

* The GUI interface has been updated slightly to be easier to use.

* Added a new option ``--version`` that just prints out the pdfCropMargins
  version number.

0.2.10 (2020-08-23)
-------------------

Bug fixes:

* Fixed minor bug in handling negative thresholds and improved display in GUI when
  ``--gsBbox`` is selected.

* Fixed a bug in the restore option which caused it to fail when pre-cropping was
  used.  It previously saved (and restored) the modified pre-crop values.

* Fixed the wait-indicator message (displayed during cropping) not becoming
  visible in recent versions of PySimpleGUI.

0.2.9 (2020-07-28)
------------------

New features:

* Users can now call the program from their Python code by importing the ``crop``
  function.

0.2.[78] (2020-05-16)
---------------------

New features:

* Negative threshold values are now allowed, and reverse the test for
  background vs. foreground.  This can be used for PDFs with dark backgrounds
  and light foregrounds.

Bug fixes:

* Minor improvements.

0.2.[3456] (2019-09-08)
-----------------------

New features:

* Added a command to write the crops to a file, mostly for testing and debugging.

Bug fixes:

* Fixed a bug with catching signals on Windows systems.

* Fixed a bug with Windows finding the fallback pdftoppm from setup.py installs.

* Fixed a faulty warning about thresholds with gs introduced with the GUI mode.

0.2.[012] (2019-08-19)
-------------------------

* Updated documentation.

* Removed typing dependency (fixed in PySimpleGUI27).

0.1.6 (2019-08-18)
------------------

Bug fixes:

* Added typing dependency for GUI with Python <= 3.4.

0.1.5 (2019-08-18)
------------------

New features:

* Added a graphical user interface (GUI) which allows PDF files to be interactively
  cropped with different settings without having to re-render the pages.

* An option ``--pageRatiosWeights`` which also takes per-margin weights to determine
  what proportion of the necessary padding to apply to each margin.

0.1.4 (2019-02-07)
------------------

New features:

* An option ``--uniformOrderStat4`` (shortcut ``-m4``) has been added to allow
  setting the order statistic (for how many smallest delta values to ignore)
  individually for each margin.

* Verbose mode now prints out the pages on which the smallest delta values were
  found, for better tuning of crop commands.

Bug fixes:

* Fixed a bug in the interaction of the ``-u``, ``-pg``, and ``-e`` options.

0.1.3 (2017-03-14)
------------------

New Features:

* Now copies over data from the document catalog to the cropped document.
  This includes, for example, the outline or bookmarks.

* There is a new option ``--docCatBlacklist`` (shortcut ``-dcb``) which can
  be used to block any particular item from being copied.  The default is
  an empty string, which copies everything possible.  To revert to the
  previous behavior of pdfCropMargins you can set ``-dcb "ALL"``.  See
  the program's help option ``-h``.

* There is another new option ``--docCatWhitelist`` (shortcut ``dcw``) which
  is a list of document catalog items to always try to copy over.  This
  list overrides the blacklist.

* There is a new option to use an order statistic in choosing the page size for
  the ``--samePageSize`` option.  The argument is the number ``n`` of pages to
  ignore in each edge calculation.  The option is ``--samePageSizeOrderStat``
  (shortcut ``-ms``).  See the program's help option ``-h``.

* Added a new option ``--setPageRatios`` (shortcut ``-spr``) which allows the
  width to height ratios of the final pages to be set.  Either top and bottom
  or left and right margins will be increased after the usual cropping to
  give the chosen ratio.

0.1.2 (2017-03-14)
------------------

* Changed code to better PEP-8 naming.

* Fixed issue where return codes were not being returned correctly on failure.

* Modified ``samePageSize`` option to only apply to pages selected by the ``pages`` option.

* Option ``-pg`` is now another synonym for ``--pages``.

0.1.1 (2017-02-27)
------------------

* Minor edits to documentation.

0.1.0 (2017-02-27)
------------------

New Features: None.

Bug Fixes: None.

Other Changes:

* Converted to have a setup.py and install using pip.

* The executable is now called pdf-crop-margins instead of pdfCropMargins.

* Local PyPDF2 is no longer packaged with it.

0.0.0 (before pip)
------------------

Initial release.

