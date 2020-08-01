# -*- coding: utf-8 -*-
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

"""

from __future__ import print_function, division, absolute_import
import sys
import signal

def main():
    """Crop with the arguments in `sys.argv`, catching any exceptions and cleaning
    up the temp directory.  Called as the entry point for `pdf-crop-margins` script.
    Only use for running as a standalone script."""
    cleanup_and_exit = sys.exit # Function to exit (in finally) before the import.
    exit_code = 0

    # Imports are done here inside the try block so some ugly (and useless) traceback
    # info is avoided on user's Ctrl-C (`KeyboardInterrupt`, `EOFError` on Windows)
    # during startup.
    try:
        from .external_program_calls import cleanup_and_exit, create_temporary_directory
        from .main_pdfCropMargins import main_crop

        # Call cleanup_and_exit at system exit, even with signal kills.
        # Note SIGINT for Ctrl-C is already handled fine by the finally.
        # (This signal-catching is probably no longer be needed for cleanup now that the
        # temp dir is created with a context manager, but it gives nicer exit messages.)
        for s in ["SIGABRT", "SIGTERM", "SIGHUP"]:
            if hasattr(signal, s): # Not all systems define the same signals.
                signal.signal(getattr(signal, s), cleanup_and_exit)

        crop()
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
        max_traceback_length = 60
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

def crop(argv_list=None):
    """Crop the PDF file using the arguments specified in `sys.argv`.  If a list is
    passed as `argv_list` then it is used instead of `sys.argv`.  This function
    can be called as a library routine of the `pdfCropMargins` package."""
    # Imports are done here so that when called as a library routine
    # the caller can handle any `KeyboardInterrupt`, `SystemExit`, or other
    # exceptions.
    from .external_program_calls import create_temporary_directory
    from .main_pdfCropMargins import main_crop
    with create_temporary_directory():
        main_crop(argv_list)

