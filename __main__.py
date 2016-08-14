#!/usr/bin/python
"""

This file allows the pdfCropMargins program to be executed by passing python
the name of the directory as a source argument.  It also allows the recursively
zipped directory contents to be passed to python as a source argument (i.e.,
without unzipping the zipfile).  For the zipfile to run, the *contents* of the
the top-level directory must be at the top-level of the zipfile (i.e., not
inside a containing directory that was recursively added to the zipfile).  So,
unfortunately, a zipfile downloaded from github cannot be directly run.

Note that on Linux machines zipped code can be made directly executable,
without a file extension.  If the zipped version of the source directory is
called pdfCropMargins.zip then these commands:

   $ echo '#!/usr/bin/python' | cat - pdfCropMargins.zip > pdfCropMargins
   $ chmod +x pdfCropMargins

will create a portable executable called pdfCropMargins that can be copied
anywhere.

"""

import sys
sys.path.insert(0, "./src")

from pdfCropMargins.pdfCropMargins import main

if __name__ == "__main__":
   main()

