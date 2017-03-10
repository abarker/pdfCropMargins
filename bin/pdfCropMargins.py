#!/usr/bin/env python
"""

Only use this script to run pdfCropMargins from the source directory itself.
If installing from pip then a script called pdf-crop-margins will be added to
your Python scripts directory (which can be added to your PATH if it is not
already there).

The relative path of this script to the source code must be fixed, so do not
move this script.  Link to it from an alias or from a simple shell script in a
directory on your PATH to use a shorter invocation command.

"""

from __future__ import print_function, division, absolute_import
import sys
import os

bin_dir = os.path.dirname(os.path.realpath(os.path.expanduser( __file__)))
package_dir = os.path.abspath(os.path.join(bin_dir, "..", "src"))
sys.path.insert(0, package_dir)
from pdfCropMargins.pdfCropMargins import main

main()

