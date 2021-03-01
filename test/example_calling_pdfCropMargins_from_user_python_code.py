#!/usr/bin/env python3
"""

Simple test of calling pdfCropMargins from a user Python script.

"""

from __future__ import print_function, division, absolute_import
import sys
import os

#bin_dir = os.path.dirname(os.path.realpath(os.path.expanduser( __file__)))
#package_dir = os.path.abspath(os.path.join(bin_dir, "..", "src"))
#sys.path.insert(0, package_dir)
from pdfCropMargins import crop

try: # Catch an exception, in this case a bad argument.
    print("running bad command-line test")
    crop(["$tpdfc/dimethylethanolamine-DMAE-andSelectedSaltsAndEsters_2002.pdf", "-gui", "-Zv"],
            string_io=False)
except BaseException as e: # Note BaseException is needed to catch a SystemExit.
    print("\nCaught exception {} running pdfCropMargins:\n   "
            .format(type(e).__name__), e, sep="")

#crop(["$tpdfc/canWeBelieveInA-PurelyUnitaryQuantumDynamics_Herbut2005.pdf", "-gui", "-pf", "-v"])
#crop(["$tpdfc/dimethylethanolamine-DMAE-andSelectedSaltsAndEsters_2002.pdf", "-gui", "-pf", "-v"])

exit_code, stdout, stderr = None, None, None
try:
    # Run capturing any SystemExit exit code and the string output.
    exit_code, stdout, stderr = crop(
            ["-h", '-ap', '12', '-p', '15', '-u', '-mo', '-su', 'old', "-pf", "-v",
             "-o", "/tmp/egg.pdf", "-pg", "9-0",
             '$tpdfc/tmp/canWeBelieveInA-PurelyUnitaryQuantumDynamics_Herbut2005.pdf'],
             string_io=True, quiet=False
          )
except BaseException as e:
    print("caught exception in test program")
    print(e)


print("== exit_code", "="*60)
print(exit_code)
print("== stdout", "="*60)
print(stdout)
print("== stderr", "="*60)
print(stderr)
print("="*60)

