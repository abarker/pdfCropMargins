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
import io

def main():
    """Crop with the arguments in `sys.argv`, catching any exceptions and cleaning
    up the temp directory.  Called as the entry point for `pdf-crop-margins` script.
    Only use for running as a standalone script.

    This function calls the `crop` routine that is the exposed API of pdfCropMargins
    but adds checks for various exceptions and signals in order to work robustuly as
    a command-line application."""
    cleanup_and_exit = sys.exit # Function to exit (in finally) before the import.
    exit_code = 0

    # Imports are done here inside the try block so some ugly (and useless) traceback
    # info is avoided on user's Ctrl-C (`KeyboardInterrupt`, `EOFError` on Windows)
    # during startup.
    try:
        from .external_program_calls import cleanup_and_exit, create_temporary_directory
        from .main_pdfCropMargins import main_crop

        # Call cleanup_and_exit at system exit, even with signal kills.
        # Note SIGINT for Ctrl-C is already handled by the except/finally.
        for s in ["SIGABRT", "SIGTERM", "SIGHUP"]:
            if hasattr(signal, s): # Not all systems define the same signals.
                signal.signal(getattr(signal, s), cleanup_and_exit)

        crop()
    except (KeyboardInterrupt, EOFError): # Windows raises EOFError on ^C.
        print("\nGot a KeyboardInterrupt, cleaning up and exiting...\n",
              file=sys.stderr)
    except SystemExit as e:
        #exit_code = int(str(sys.exc_info()[1])) # The number sys.exit(n) called with.
        exit_code = e.code
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
        for i in range(20): # Loop to be sure to catch multiple Ctrl-C exceptions.
            try:
                cleanup_and_exit(exit_code)
                break
            except (KeyboardInterrupt, EOFError): # Windows raises EOFError on ^C.
                continue

class CapturingTextStream:
    """This class allows stdout and stderr to be temporarily redefined to capture
    the output (and to optionally quiet it)."""
    def __init__(self, outstream, quiet=True):
        """Will usually be passed `sys.stdout` or `sys.stderr` and an `IOStream` as
        arguments."""
        self.quiet = quiet
        self.outstream = outstream
        self.stringio = io.StringIO()

    def write(self, s):
        stringio_retval = self.stringio.write(s)
        if not self.quiet:
            pass
            return self.outstream.write(s)
        return stringio_retval

    def getvalue(self):
        return self.stringio.getvalue()

    def __getattr__(self, attr):
        return getattr(self.outstream, attr)


def crop(argv_list=None, quiet=False, string_io=False):
    """Crop the PDF file using the arguments specified in `sys.argv`.  If a list is
    passed as `argv_list` then it is used instead of `sys.argv`.  This function
    can be called as a library routine for running the `pdfCropMargins` program.

    The function returns three values.  The first return value is either `None`
    or, in the event of a `SystemExit` exception, the exit code.  (A
    `SystemExit` is the usual way pdfCropMargins exits.)  The second two
    arguments always have `None` values unless either the `string_io` or the
    `quiet` keyword option is set true (see below).

    The `string_io` and `quiet` keyword options, if either is selected,
    temporarily redefine `sys.stdout` and `sys.stderr` to intercept the usual
    print commands from pdfCropMargins and save the text as strings.  If
    `string_io` is true then the second two return values are strings holding
    the stdout and stderr output, respectively.  If `quiet` is true then no
    echoing to stdout or stderr is performed while pdfCropMargins runs.  The
    `quiet` option implies the `string_io` option, so the string values are
    returned in both cases.

    The pdfCropMargins program normally raises `SystemExit` on correct
    operation or for error conditions which are detected and handled.  The
    `crop` function catches `SystemExit` and returns the error code.  The
    `stderr` string value may be needed to diagnose the cause of a nonzero exit
    code if `quiet` is set true.

    Unexpected exits, such as exceptions from dependencies or program bugs, can
    still occur.  Such exceptions are passed up to the caller.  Similarly,
    interrupts are not trapped or handled in the `crop` function."""

    # Imports are done here so that when `crop` is called as a library routine
    # the caller can handle any `KeyboardInterrupt`, `SystemExit`, or other
    # exceptions that might occur during to the imports.
    from .external_program_calls import (create_temporary_directory,
                                         uninterrupted_remove_program_temp_directory)
    from .main_pdfCropMargins import main_crop

    exit_code = None

    try:
        if string_io or quiet:
            try: # Redirect stdout and stderr temporarily.
                old_sys_stdout, old_sys_stderr = sys.stdout, sys.stderr
                #sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
                sys.stdout = CapturingTextStream(sys.stdout, quiet=quiet)
                sys.stderr = CapturingTextStream(sys.stderr, quiet=quiet)
                with create_temporary_directory():
                    main_crop(argv_list)
            except Exception as e:
                raise # TODO: Maybe set stdout_str and stderr_str as attrs of e or print them.
            except SystemExit as e:
                exit_code = e.code
            finally: # Restore stdout and stderr.
                stdout_str, stderr_str = sys.stdout.getvalue(), sys.stderr.getvalue()
                sys.stdout, sys.stderr = old_sys_stdout, old_sys_stderr
            return exit_code, stdout_str, stderr_str
        else:
            try:
                with create_temporary_directory():
                    main_crop(argv_list)
            except SystemExit as e:
                exit_code = e.code
            return exit_code, None, None

    finally: # In case race conditions prevent execution of the context manager __exit__.
        uninterrupted_remove_program_temp_directory()

