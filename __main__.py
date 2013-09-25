#!/usr/bin/python
"""

This file allows the pdfCropMargins program to be executed simply by
calling python on the zipped directory (i.e., without unzipping it),
or when python is passed the pathname of the directory itself.

"""

from pdfCropMargins import main

if __name__ == "__main__":
   main()

