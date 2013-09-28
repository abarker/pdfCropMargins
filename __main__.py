#!/usr/bin/python
"""

This file allows the pdfCropMargins program to be executed simply by
calling python on the zipped directory (i.e., without unzipping it),
or when python is passed the pathname of the directory itself.

Note that on Linux machines the zipped directory can be made directly
executable, without a file extension.  If the zipped version of the source
directory is called pdfCropMargins_master.zip then these commands:

   $ echo '#!/usr/bin/python' | cat - pdfCropMargins_master.zip > pdfCropMargins
   $ chmod +x pdfCropMargins

will create a portable executable called pdfCropMargins that can be copied
anywhere.

"""

from pdfCropMargins import main

if __name__ == "__main__":
   main()

