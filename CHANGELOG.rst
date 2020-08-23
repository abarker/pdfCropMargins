.. :changelog:

History
=======

0.2.10 (2020-XX-XX)
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

