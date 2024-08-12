.. :changelog:

History
=======

2.1.4 (2024-XX-XX)
------------------

New features:

* Added the option ``--replaceOriginal`` which implies the ``--modifyOriginal`` option
  but removes the file instead of replacing it.

* Added the option ``--uniform4`` which allows for selecting which margins the
  uniform cropping is applied to.

* Added the option ``--samePageSize4`` which allows for selecting which margins
  the same page size option is applied to.

2.1.3 (2024-06-05)
------------------

Bug fixes:

* Vendorized the LGPL version 4 of PySimpleGUI since it changed license and
  took down older versions from PyPI.

2.1.2 (2024-04-13)
------------------

New features:

* Added the options ``--centerText``,  ``--centerTextHoriz``,
  ``--centerTextVert``,  and ``--centeringStrict`` to center text on the pages
  after cropping.

Bug fixes:

* Fixed a bug in ``--keepVertCenter`` and ``--keepHorizCenter`` when cropping is restricted
  to certain pages.

2.1.[0-1] (2024-04-29)
----------------------

Changes:

* The version of pySimpleGui to install is restricted to less than version 5,
  since it started requiring registration at that point.

* The default for what boxes to set is now by default only the mediabox.  This
  is because of unknown problems causing "cropbox could not be written"
  exceptions from PyMuPDF.  It will try writing the boxes, if they are
  selected with ``--boxesToSet``, but may or may not actually set them.

2.0.3 (2023-07-04)
------------------

* Work on a resource warning that appeared at times.

2.0.[12] (2023-06-22)
---------------------

New features:

* Added the option ``--setSamePageSize`` (``-ssp``) which sets all the page
  boxes to user-passed values instead of calculating the containing page
  size.

2.0.0 (2023-06-14)
------------------

Changes:

* All internal PDF processing is now done with PyMuPDF.  The PyPDF dependency
  has been removed.

* The program now uses PyMuPDF for all internal PDF processing instead of
  PyPDF.  The PyPDF dependency has been removed, and PyMuPDF is a required
  depencency.

* The PyMuPDF program is much stricter about setting page boxes than PyPDF, in
  order to avoid inconsistent situations.  Setting the MediaBox automatically
  resets all the other boxes (CropBox, etc.) to their defaults.  The MediaBox
  is always set first.  By default crops still set the MediaBox and CropBox,
  but the other boxes will be reset.

* All the other boxes must be completely contained in the MediaBox to be set.
  If not (when using the ``--boxesToSet`` option) a warning will be issued and
  the action will be ignored.

* The ArtBox can no longer be used to save restore information.  The restore
  information is instead saved in the XML metadata.  Documents that were
  cropped by earlier versions will automatically have their ArtBox data
  transferred to XML restore metadata unless the ``--noundosave`` option is
  used.

* The options ``--docCatBlacklist`` and ``--docCatWhitelist`` have been removed
  since PyMuPDF automatically retains the full document catalog.

1.2.0 (2023-03-12)
------------------

Changes:

* Added deprecation warnings for the options ``--docCatBlacklist``,
  ``--docCatWhitelist``, ``--gsRender``, and ``--gsBbox``.  They will be
  removed in version 3.0.  The latter two have equivalent ``-c`` options.  The
  former two no longer work because the PyPDF2 dependency will be fully
  replaced with PyMuPDF.  PyMuPDF by default copies over the full document
  catalog and should be more compliant with PDF specifications.

1.1.1[7-8] (2023-03-12)
-----------------------

New features:

* Added the option ``--screenRes`` to pass in the full screen resolution (if
  the size-detection algorithm fails) and ``-guiFontSize`` to set the font size
  in the GUI.

Changes:

* Python 3.7 now required due to requirements of Pillow and PyMuPDF.

Bug fixes:

* Sizing of the GUI for smaller screen resolutions has been improved.

1.1.1[4-6] (2023-02-17)
-----------------------

New features:

* Windows can now be resized and the preview will be redrawn to match.
  Page rendering to the GUI has also been improved.

Bug fixes:

* Added a fallback for some systems (KDE) which were failing to detect the
  correct screen size for the GUI.

1.1.13 (2023-01-25)
-------------------

Bug fixes:

* Fixed a bug where a file with unreadable metadata can have a bad attribute access.

1.1.12 (2023-01-24)
-------------------

Bug fixes:

* The precision of the cropped point values for the new margins is now limited (to 8 after
  the decimal) to avoid possible problems with some PDF viewers.

1.1.1[0-1] (2023-01-01)
-----------------------

New features:

* Added an option ``--prevCropped`` (``-pc``) which just tests whether or not the document was
  previously cropped with pdfCropMargins.  This is meant for scripting use.

Bug fixes:

* Fixed a bug in returning error codes when running from the command line.

1.1.9 (2022-12-29)
------------------

Bug fixes:

* Pinned PyPDF2 version to < 3.0.0 because of breaking changes.

1.1.8 (2022-12-09)
------------------

New features:

* Added the new ``--cropSafeMin4`` (``-csm4``) option to specify a safe minimum
  margin other than the bounding box.

* The two new options ``--keepHorizCenter`` (``-khc``) and ``--keepVertCenter``
  (``-kvc``) have been added.  These options ensure that the respective
  relative horizontal and vertical centers of pages remain the same (by
  cropping the minimum of the two delta values on each page).

Bug fixes:

* Save previous state for uniform checkbox to restore after being implied/disabled.

* Get cropSafe working more correctly with page ranges.

1.1.7 (2022-12-09)
------------------

New features:

* Implement the new ``--cropSafe`` (``-cs``) option which ensures safe crops if
  enabled.

Bug fixes:

* Workaround for a bug in the GUI uniform button.

1.1.[2-6] (2022-12-09)
----------------------

New features:

* The GUI layout has been rearranged for more intuitive use of the options that take
  four values, one for the left, bottom, right, and top margins.

* The GUI now displays the minimum cropping delta values as buttons which take you
  to that page.  This is helpful for fine-tuning cropping without cropping-out useful
  information.

* Page numbers and uniformOrderstat widgets in the GUI were changed to spinners.

Bug fixes and maintenance:

* Internally, functions were renamed to match the recent PyPDF2 deprecations.

* Fixed bug caused by adding pdfcropmargins as an alias.

* Fixed bug when uniform mode not selected, and extend min delta display to both
  cases.

1.1.[0-1] (2022-12-07)
----------------------

New features:

* The alias ``pdfcropmargins`` can now be used instead of ``pdf-crop-margins``
  to run the program from the command line.

Bug fixes and maintenance:

* Upgraded to Python 3.6 minimum requirement with pyupgrade.

* The GUI dependencies are now part of the standard install (although the program
  will still run without them if the GUI is not required).

* Dependency versions updated for security and functionality changes.

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

* Import of ``PdfReadError`` now tries the ``errors`` module and then the ``utils`` module.

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

