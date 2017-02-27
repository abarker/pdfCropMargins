#!/bin/bash
#
# Usage (assuming a file named crop):
#    crop <argumentsToPdfCropMargins>

# This simple Bash convenience script just calls pdfCropMargins with certain
# settings.  Users can easily modify the file to their preferences.
#
# Copy this file to your bin directory (as 'crop' or whatever you prefer) and
# make it executable (with 'chmod +x ~/bin/crop').

# -v             show verbose output
# -pv acroread   use acroread to view the output
# -u -s          make all pages the same size, uniformly cropped
# -pf            use 'cropped_' as a prefix (not suffix) on default output files
# "$@"           pass along any other command-line options unchanged

pdf-crop-margins \
   -v \
   -pv acroread \
   -u -s \
   -pf \
   "$@"

