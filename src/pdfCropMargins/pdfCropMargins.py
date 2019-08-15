#!/usr/bin/python
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

from __future__ import print_function, division, absolute_import
import sys
from .prettified_argparse import parse_command_line_arguments
# Import the prettified argparse module and the text of the manpage documentation.
from .manpage_data import cmd_parser

def get_help_for_option_string(cmd_parser, option_string):
    import textwrap
    wrapper = textwrap.TextWrapper(initial_indent="", subsequent_indent="", width=75)
    """Extract the help message for an option from an argparse command parser."""
    for a in cmd_parser._actions:
        if "--" + option_string in a.option_strings:
            help_text = textwrap.dedent(a.help)
            help_text = wrapper.fill(help_text)
            help_text = help_text.replace("^^n", "\n")
            print(help_text)
            print()
            return a.option_strings, help_text
    return None

def main():
    """Run main, catching any exceptions and cleaning up the temp directories."""

    cleanup_and_exit = sys.exit # Function to do cleanup and exit before the import.
    exit_code = 0

    # Imports are done here inside the try block so some ugly (and useless)
    # traceback info is avoided on user's ^C (KeyboardInterrupt, EOFError on Windows).
    try:
        from . import external_program_calls as ex # Creates tmp dir as a side effect.
        cleanup_and_exit = ex.cleanup_and_exit # Switch to the real one, deletes temp dir.

        from . import main_pdfCropMargins # Imports external_program_calls, don't do first.

        while True:
            # Parse the command-line arguments and set the variable args.  In module scope so
            # all the functions can easily access the arguments they need.

            #print(get_help_for_option_string(cmd_parser, "percentRetain"))
            parsed_args = parse_command_line_arguments(cmd_parser)

            if parsed_args.gui:
                from . import gui
                args = sys.argv[:] # Save these in case they're needed in loop.
                gui.display_gui(parsed_args)
                # TODO: Call gui fun, return the new args list.
                # Then command parse the new args (set to sys.argv) and call main crop routine.
                # Pass in cmd_parser or actions object to extract tooltips, too.
            else:
                # Call the "real" main routine.
                main_pdfCropMargins.main_crop(parsed_args)

            if not parsed_args.gui:
                break

    except (KeyboardInterrupt, EOFError): # Windows raises EOFError on ^C.
        print("\nGot a KeyboardInterrupt, cleaning up and exiting...\n",
              file=sys.stderr)

    except SystemExit:
        exit_code = sys.exc_info()[1]
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
        # raise # Re-raise the error.

    finally:
        # Some people like to hit multiple ^C chars, which kills cleanup.
        # Call cleanup again each time.
        for i in range(30): # Give up after 30 tries.
            try:
                cleanup_and_exit(exit_code)
            except (KeyboardInterrupt, EOFError):
                continue


#
# Run when invoked as a script.
#

if __name__ == "__main__":

    main()

