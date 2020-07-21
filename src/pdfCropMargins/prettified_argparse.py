"""

This module defines classes for redirecting `sys.stdout` and `sys.stderr` in
order to postprocess (prettify) the help and usage messages from the argparse
class.  Generally only the `parse_command_line_arguments` function will be
imported from it.

This module also defines a self-flushing output stream to avoid having to
explicitly run Python with the '-u' option in Cygwin windows.  It provides the
function::

   parse_command_line_arguments

which applies the prettifier to an argparse parser and resets sys.stdout to
an automatic-flushing version.

The usage is::

   from prettified_argparse import parse_command_line_arguments
   from manpage_data import cmd_parser

The actual argparse parser and documentation text are in `manpage_data.py`.
Somewhere in the calling program, the imported function should be called as::

    args = parse_command_line_arguments(cmd_parser)

Note that the standard `TextWrapper` fill and wrap routines used in `argparse`
do not strip out multiple whitespace like many fill programs do.  See the
`RedirectHelp` comment for the changes to the standard `argparse` formatting.

=====================================================================

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

"""

from __future__ import print_function, division, absolute_import
import textwrap
import re
import sys
import os

# TODO: This basename may differ when run as an entry point script.
prog_name = os.path.basename(sys.argv[0])
# Note when a directory is run as a command name it can be something like "."
# which looks nicer expanded.  Argparse currently uses the unexpanded form.
abs_prog_name = os.path.basename(os.path.abspath(sys.argv[0]))
# Improve the usage message when run from a file with a different name (such
# as __main__.py).
if not abs_prog_name.startswith("pdfCropMargins"):
    abs_prog_name += " (pdfCropMargins)"

# These strings are directly replaced in the argparse help and usage output stream.
# The string on the right of the tuple replaces the string on the left.  The
# string directly after "Usage" is currently not changed.
help_string_replacement_pairs = (
    ("usage: ", "^^nUsage: "),
    ("positional arguments:", "Positional arguments:^^n"),
    ("optional arguments:", "Optional arguments:^^n"),
    ("show this help message and exit", "Show this help message and exit.^^n"),
    ("%s: error: too few arguments" % prog_name, textwrap.fill(
     "^^nError in arguments to %s: an input document filename is required.^^n"
     % abs_prog_name)),
    (prog_name + ": error:", "Error in "+abs_prog_name+":")
)


class RedirectHelp(object):
    """This class allows for redirecting stdout in order to prettify the output
    of argparse's help and usage messages (via a postprocessor).  An outstream
    like stdout is simply set equal to an instance of this class, passed the
    original outstream in the initializer.  This class just reformats before
    passing values through.

    The postprocessor does a string replacement for all the pairs defined in
    the user-defined sequence help_string_replacement_pairs.  It also adds the
    following directives to the formatting language:

       ^^s          replaced with a space, correctly preserved by ^^f format
       \a           the bell control char is also replaced with preserved space
       ^^f ... ^^f  reformat all the text between these directives
       ^^n          replaced with a newline (after any ^^f format)

    Formatting with ^^f converts any sequence of two or more newlines into a
    single newline, i.e., a paragraph break.  Multiple (non-preserved)
    whitespaces are converted to a single white space, and the text in
    paragraphs is line-wrapped with a new indent level."""

    def __init__(self, outstream, help_string_replacement_pairs,
                 init_indent=5, subs_indent=5, line_width=76):
        """Will usually be passed `sys.stdout` or `sys.stderr` as an outstream
        argument.  The pairs in the variable `help_string_replacement_pairs`
        are all applied to the any returned text as postprocessor string
        replacements.  The initial indent of formatted sections is set to
        `init_indent`, and subsequent indents are set to `subs_indent`.  The
        line width in formatted sections is set to `line_width`."""
        self.outstream = outstream
        self.help_string_replacement_pairs = help_string_replacement_pairs
        self.init_indent = init_indent
        self.subs_indent = subs_indent
        self.line_width = line_width

    def write(self, s):
        """First preprocess the string `s` to prettify it (assuming it is argparse
        help output).  Then write the result to the outstream associated with the
        class."""
        pretty_str = s
        for pair in self.help_string_replacement_pairs:
            pretty_str = pretty_str.replace(pair[0], pair[1])
        # Define ^^s as the bell control char for now, so fill will treat it right.
        pretty_str = pretty_str.replace("^^s", "\a")

        def do_fill(match_obj):
            """Fill function for regexp to apply to ^^f matches."""
            st = pretty_str[match_obj.start()+3:match_obj.end()-3] # get substring
            st = re.sub("\n\\s*\n", "^^p", st).split("^^p") # multi-new to para
            st = [" ".join(s.split()) for s in st] # multi-whites to single
            wrapper = textwrap.TextWrapper( # indent formatted paras
                initial_indent=" "*self.init_indent,
                subsequent_indent=" "*self.subs_indent,
                width=self.line_width)
            return "\n\n".join([wrapper.fill(s) for s in st]) # wrap each para

        # Do the fill on all the fill sections.
        pretty_str = re.sub(r"\^\^f.*?\^\^f", do_fill, pretty_str, flags=re.DOTALL)
        pretty_str = pretty_str.replace("\a", " ") # bell character back to space
        pretty_str = pretty_str.replace("^^n", "\n") # replace ^^n with newline
        self.outstream.write(pretty_str)
        self.outstream.flush() # automatically flush each write

    def __getattr__(self, attr):
        """For any undefined attributes return the value associated with the outstream
        saved with the class."""
        return getattr(self.outstream, attr)


class SelfFlushingOutstream(object):
    """This class allows stdout and stderr to be redefined so that they are
    automatically flushed after each write.  (The same thing can be achieved via
    the '-u' flag on the Python command line.)  This helps when running in
    Cygwin terminals.  Class is independent of the `RedirectHelp` class above."""

    def __init__(self, outstream):
        """Will usually be passed sys.stdout or sys.stderr as an argument."""
        self.outstream = outstream

    def write(self, s):
        self.outstream.write(s)
        self.outstream.flush()

    def __getattr__(self, attr):
        return getattr(self.outstream, attr)


def parse_command_line_arguments(argparse_parser, argv_list=None, init_indent=5,
                                 subs_indent=5, line_width=76, self_flushing=False):
    """Main routine to call to execute the command parsing.  Returns an object
    from argparse's `parse_args()` routine.  If `argv_list` is set then it will
    be used instead of `sys.argv`."""
    # Redirect stdout and stderr to prettify help or usage output from argparse.
    old_stdout = sys.stdout # save stdout
    old_stderr = sys.stderr # save stderr
    sys.stdout = RedirectHelp(sys.stdout, help_string_replacement_pairs,
            init_indent, subs_indent, line_width) # redirect stdout to add postprocessor
    sys.stderr = RedirectHelp(sys.stderr, help_string_replacement_pairs,
            init_indent, subs_indent, line_width) # redirect stderr to add postprocessor

    # Run the actual argument-parsing operation via argparse.
    parsed_args = argparse_parser.parse_args(args=argv_list)

    # The argparse class has finished its argument-processing, so now no more
    # usage or help messages will be printed.  So restore stdout and stderr
    # to their usual settings.
    if self_flushing:
        sys.stdout = SelfFlushingOutstream(old_stdout)
        sys.stderr = SelfFlushingOutstream(old_stderr)
    else:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    return parsed_args

