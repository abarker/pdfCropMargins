# -*- coding: utf-8 -*-
# Note that using the shebang "usr/bin/env python" does not set the process
# name to pdfCropMargins in Linux (for things like top, ps, and killall).
"""

pdfCropMargins -- a program to crop the margins of PDF files
Copyright (C) 2014 Allen Barker (Allen.L.Barker@gmail.com)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Source code site: https://github.com/abarker/pdfCropMargins

=====================================================================

A command-line application to crop the margins of PDF files.  Cropping the
margins can make it easier to read the pages of a PDF document -- whether the
document is printed or displayed on a screen -- because the fonts appear
larger.  Margin-cropping is also useful at times when one PDF is included in
another as a graphic.  Many options are available.

To see the formatted documentation, run::
   pdfCropMargins -h | more
or::
   python pdfCropMargins -h | more

This is the initial starting script, but it just calls `mainCrop` from
`main_pdfCropMargins.py`, which does the real work.  Its only purpose is to
handle errors and make sure that any temp directories are cleaned up.  It tries
to gracefully handle ^C characters from the user (`KeyboardInterrupt`) to stop
the program and clean up.

"""

# Possible future enhancements:
#
# 1) Consider defining a command-line option which will print out either a bash
# script or a DOS script that users can modify and use.  Or maybe a config file.
#
# 2) Have -ea and -oa options that do absolute crops on even and odd
# differently.  Similarly, -ea4 and -oa4 for individual margins.  Similarly
# -eap and -oap for even vs. odd absolute pre-crops.  Or maybe just have an
# option to easily *only* crop the even or odd pages, so user can run usual
# program twice.  --even-only (-eo), --odd-only (-oo)
#
# 3) It would be possible to ask for changes to any parameters before deleting
# the temp file.  Then they could be recomputed very quickly, without having to
# recalculate the bounding boxes.
#
# 4) An option to run a test comparison would be useful for a test suite.  Just
# dump both the original crop values and the final ones to a file in some
# standard format.  Later compare between files.  Other things could also be
# checked; basically dump the verbose output except not so sensitive to minor
# text changes and use "close enough" for floating point value equality.
#
# 5) An option 'safeAbsolute' which can be turned on to keep absolute crops
# from exceeding the bounding box sizes.  But need to define semantics with
# and without uniform cropping and same page size.
#
# 6) Unzip a file if a zipped file is detected.  Maybe a `tryUnzip` option.

from __future__ import print_function, division, absolute_import
import sys
import signal

def main():
    """Run main, catching any exceptions and cleaning up the temp directories."""
    cleanup_and_exit = sys.exit # Function to exit (in finally) before the import.
    exit_code = 0

    # Imports are done here inside the try block so some ugly (and useless)
    # traceback info is avoided on user's ^C (KeyboardInterrupt, EOFError on Windows).
    try:

        # This import creates a tmp dir as a side effect.
        # Switch cleanup_and_exit to the real one, which deletes temp dir.
        from .external_program_calls import cleanup_and_exit

        # Call cleanup_and_exit at system exit, even with signal kills.
        # (This could alternately be called just after defining the function.)
        # Note SIGINT for Ctrl-C is already handled fine by the finally.
        for s in [signal.SIGABRT, signal.SIGTERM, signal.SIGHUP]:
            signal.signal(s, cleanup_and_exit)

        # Below import also imports external_program_calls, don't do it first.
        from .main_pdfCropMargins import main_crop
        main_crop()

    except (KeyboardInterrupt, EOFError): # Windows raises EOFError on ^C.
        print("\nGot a KeyboardInterrupt, cleaning up and exiting...\n",
              file=sys.stderr)

    except SystemExit:
        exit_code = int(str(sys.exc_info()[1])) # The number sys.exit(n) called with.
        print()

    except:
        # Echo back the unexpected error so the user can see it.
        print("\nCaught an unexpected exception in the pdfCropMargins program.",
                                                               file=sys.stderr)
        print("Unexpected error: ", sys.exc_info()[0], file=sys.stderr)
        print("Error message   : ", sys.exc_info()[1], file=sys.stderr)
        print()
        exit_code = 1
        import traceback
        max_traceback_length = 30
        traceback.print_tb(sys.exc_info()[2], limit=max_traceback_length)
        # raise

    finally:
        # Clean up the temp file directory.  Note some people like to hit multiple
        # ^C chars, which kills cleanup.  The loop calls cleanup again each time.
        for i in range(30): # Give up after 30 tries.
            try:
                cleanup_and_exit(exit_code)
            except (KeyboardInterrupt, EOFError):
                continue


