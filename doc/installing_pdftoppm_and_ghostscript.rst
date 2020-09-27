
Installing pdftoppm and/or Ghostscript
======================================

Some options of pdfCropMargins depend on either the Ghostscript program or the
pdftoppm program being installed (and locatable) on the system.  For Windows
users a version of a pdftoppm binary (xpdf 4.01.01) is packaged with the
program and will be used as a fallback if no other version can be found.
 
pdftoppm
--------

* **Linux**: The pdftoppm program is standard in most Linux distributions
  and is easy to install in Cygwin.  It is currently part of the Poppler PDF
  tools, so that package should be installed on Linux and Cygwin if the
  `pdftoppm` command is not available.  On Ubuntu the command is::

     sudo apt install poppler-utils

* **Windows**: In Windows pdftoppm is not as easy to install, but a
  collection of PDF tools `found here
  <http://www.foolabs.com/xpdf/download.html>`_ includes pdftoppm.  That
  version is bundled with the software and will be used as a fallback on
  Windows if neither Ghostscript nor the system pdftoppm program can be
  found.

Ghostscript
-----------

* **Linux**: Ghostscript is in the repos of most Linux distributions and is
  easy to install on Windows and in Cygwin.  On Ubuntu the command is::

     sudo apt install ghostscript

* **Windows**: The Windows install page is `located here
  <http://www.ghostscript.com/download/gsdnld.html>`_; the non-commercial
  GPL version on that page should work fine for most people.  Add the
  directory of the executable ``gswin64c.exe`` (or the 32 bit version if you
  installed that) to your Windows system path so it is discoverable (and
  runnable from the command shell).  On Windows 10 the place to go is:: 

     Start -> Control Panel -> System and security -> System -> Advanced system settings

  Now click "Environment Variables" and then double click on the user
  variable ``Path``.  Click "New" and browse to the directory to add
  (something like ``C:\Program Files\gs\gs9.27\bin``).  Restart your command
  shell for the change to be recognized.

