#!/usr/bin/env python3
"""

Simple test of calling pdfCropMargins from a user Python script.

"""

from __future__ import print_function, division, absolute_import
import sys
import os

bin_dir = os.path.dirname(os.path.realpath(os.path.expanduser( __file__)))
package_dir = os.path.abspath(os.path.join(bin_dir, "..", "src"))
sys.path.insert(0, package_dir)
from pdfCropMargins import crop

try:
    crop(["~/papersToRead/dimethylethanolamine-DMAE-andSelectedSaltsAndEsters_2002.pdf", "-gui", "-Zv"])
except BaseException as e:
    print("\nBad command args!  Exception is:\n", e, sep="")

crop(["~/papersToRead/canWeBelieveInA-PurelyUnitaryQuantumDynamics_Herbut2005.pdf", "-gui", "-pf", "-v"])
crop(["~/papersToRead/dimethylethanolamine-DMAE-andSelectedSaltsAndEsters_2002.pdf", "-gui", "-pf", "-v"])

