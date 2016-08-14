#!/bin/bash
#
# Usage crop <argumentsToPdfCropMargins>
#
# This simple Bash convenience script just calls pdfCropMargins with certain
# settings that I like to use.  Set the path in this script to the path of the
# pdfCropMargins Python script on your system.  Then copy it to your bin
# directory as 'crop' and make it executable (with 'chmod +x ~/bin/crop').
# Modify according to your preferences.

# -v             show verbose output
# -pv acroread   use acroread to view the output
# -u -s          make all pages the same size, uniformly cropped
# -pf            use 'cropped_' as a prefix (not suffix) on default output files
# "$@"           pass along any other command-line options unchanged

python ~/SET_THIS_PATH_TO_THE_LOCATION_ON_YOUR_SYSTEM/src/pdfCropMargins \
   -v \
   -pv acroread \
   -u -s \
   -pf \
   "$@"

