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
    crop(["$tpdfc/dimethylethanolamine-DMAE-andSelectedSaltsAndEsters_2002.pdf", "-gui", "-Zv"],
            string_io=True)
except BaseException as e: # Note BaseException is needed to catch a SystemExit.
    print("\nException running pdfCropMargins:\n   ", e, sep="")

#crop(["$tpdfc/canWeBelieveInA-PurelyUnitaryQuantumDynamics_Herbut2005.pdf", "-gui", "-pf", "-v"])
#crop(["$tpdfc/dimethylethanolamine-DMAE-andSelectedSaltsAndEsters_2002.pdf", "-gui", "-pf", "-v"])

# Run capturing any SystemExit exit code and the string output.
exit_code, stdout, stderr = crop(
        ['-ap', '12', '-p', '15', '-u', '-mo', '-su', 'old', "-pf", "-v",
         "-o", "/tmp/egg.pdf",
         '$tpdfc/tmp/canWeBelieveInA-PurelyUnitaryQuantumDynamics_Herbut2005.pdf'],
         string_io=True
      )

print("exit_code:\n   ", exit_code)
print("stdout:\n   ", stdout)
print("stderr:\n   ", stderr)

