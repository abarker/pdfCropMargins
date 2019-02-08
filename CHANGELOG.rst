.. :changelog:

History
=======

0.1.4 (2019-02-07)
------------------

New features:

* An option ``--uniformOrderStat4`` (shortcut ``-m4``) has been added to allow
  setting the order statistic (for how many smallest delta values to ignore)
  individually for each margin.

* Verbose mode now prints out the pages on which the smallest delta values were
  found, for better tuning of crop commands.

Bug fixes:

* Fixed a bug in the interaction of the `-u`, `-pg`, and `-e` options.

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

