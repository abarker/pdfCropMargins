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

Project web site: https://abarker.github.io/pdfCropMargins
Source code site: https://github.com/abarker/pdfCropMargins

=====================================================================

This module defines classes for redirecting sys.stdout and sys.stderr in order
to postprocess (prettify) the help and usage messages from the argparse class.
It also defines a self-flushing output stream to avoid having to explicitly run
Python with the '-u' option in Cygwin windows.  It provides the function ::

   parseCommandLineArguments

which applies the prettifier to an argparse parser and resets sys.stdout to
an automatic-flushing version.

This file can be copied inline when you really want a single-file script.
Otherwise, the usage is:

   from prettified_argparse import parseCommandLineArguments
   from manpage_data import cmdParser

The actual argparse parser and documentation text are in manpage_data.py.
Somewhere in the calling program, the imported function should be called as:

    args = parseCommandLineArguments(cmdParser)

Note that the standard TextWrapper fill and wrap routines used in argparse
do not strip out multiple whitespace like many fill programs do.  See the
RedirectHelp comment for the changes to the standard argparse formatting.

"""

# Consider implementing an optional config file to set any of the command-line
# arguments.  Note that argparse does not depopulate the sys.argv list.
#
# See the top answer here:
# http://stackoverflow.com/questions/6133517/parse-config-file-environment-and-command-line-arguments-to-get-a-single-coll

import textwrap
import re
import sys
import os

progName = os.path.basename(sys.argv[0])
# Note when a directory is run as a command name it can be something like "."
# which looks nicer expanded.  Argparse currently uses the unexpanded form.
absProgName = os.path.basename(os.path.abspath(sys.argv[0]))
# Improve the usage message when run from a file with a different name (such
# as __main__.py).
if not absProgName.startswith("pdfCropMargins"): absProgName += " (pdfCropMargins)"

# These strings are directly replaced in the argparse help and usage output stream.
# The string on the right of the tuple replaces the string on the left.  The
# string directly after "Usage" is currently not changed.
helpStringReplacementPairs = (
    ("usage: ", "^^nUsage: "),
    ("positional arguments:", "Positional arguments:^^n"),
    ("optional arguments:", "Optional arguments:^^n"),
    ("show this help message and exit", "Show this help message and exit.^^n"),
    ("%s: error: too few arguments" % progName, textwrap.fill(
     "^^nError in arguments to %s: an input document filename is required.^^n"
     % absProgName)),
    (progName + ": error:", "Error in "+absProgName+":")
)


class RedirectHelp(object):

    """This class allows us to redirect stdout in order to prettify the output
    of argparse's help and usage messages (via a postprocessor).  The
    postprocessor does a string replacement for all the pairs defined in the
    user-defined sequence helpStringReplacementPairs.  It also adds the following
    directives to the formatting language:
       ^^s          replaced with a space, correctly preserved by ^^f format
       \a           the bell control char is also replaced with preserved space
       ^^f ... ^^f  reformat all the text between these directives
       ^^n          replaced with a newline (after any ^^f format)
    Formatting with ^^f converts any sequence of two or more newlines into a
    single newline, i.e., a paragraph break.  Multiple (non-preserved)
    whitespaces are converted to a single white space, and the text in
    paragraphs is line-wrapped with a new indent level.
    """

    def __init__(self, outstream, helpStringReplacementPairs,
                 initIndent=5, subsIndent=5, lineWidth=76):
        """Will usually be passed sys.stdout or sys.stderr as an outstream
        argument.  The pairs in the variable helpStringReplacementPairs variable
        are all applied to the any returned text as postprocessor string
        replacements.  The initial indent of formatted sections is set to
        initIndent, and subsequent indents are set to subsIndent.  The line width
        in formatted sections is set to lineWidth."""
        self.outstream = outstream
        self.helpStringReplacementPairs = helpStringReplacementPairs
        self.initIndent = initIndent
        self.subsIndent = subsIndent
        self.lineWidth = lineWidth

    def write(self, s):
        prettyStr = s
        for pair in self.helpStringReplacementPairs:
            prettyStr = prettyStr.replace(pair[0], pair[1])
        # Define ^^s as the bell control char for now, so fill will treat it right.
        prettyStr = prettyStr.replace("^^s", "\a")

        def doFill(matchObj):
            """Fill function for regexp to apply to ^^f matches."""
            st = prettyStr[matchObj.start()+3:matchObj.end()-3] # get substring
            st = re.sub("\n\s*\n", "^^p", st).split("^^p") # multi-new to para
            st = [" ".join(s.split()) for s in st] # multi-whites to single
            wrapper = textwrap.TextWrapper( # indent formatted paras
                initial_indent=" "*self.initIndent,
                subsequent_indent=" "*self.subsIndent,
                width=self.lineWidth)
            return "\n\n".join([wrapper.fill(s) for s in st]) # wrap each para
        # do the fill on all the fill sections
        prettyStr = re.sub(r"\^\^f.*?\^\^f", doFill, prettyStr, flags=re.DOTALL)
        prettyStr = prettyStr.replace("\a", " ") # bell character back to space
        prettyStr = prettyStr.replace("^^n", "\n") # replace ^^n with newline
        self.outstream.write(prettyStr)
        self.outstream.flush() # automatically flush each write

    def __getattr__(self, attr):
        return getattr(self.outstream, attr)


class SelfFlushingOutstream(object):
    """This class allows stdout and stderr to be redefined so that they are
    automatically flushed after each write.  (The same thing can be achieved via
    the '-u' flag on the Python command line.)  This helps when running in
    Cygwin terminals.  Class is independent of the RedirectHelp class above."""

    def __init__(self, outstream):
        """Will usually be passed sys.stdout or sys.stderr as an argument."""
        self.outstream = outstream

    def write(self, s):
        self.outstream.write(s)
        self.outstream.flush()

    def __getattr__(self, attr):
        return getattr(self.outstream, attr)


def parseCommandLineArguments(argparseParser, initIndent=5, subsIndent=5, lineWidth=76):
    """Main routine to call to execute the command parsing.  Returns an object
    from argparse's parse_args() routine."""
    # Redirect stdout and stderr to prettify help or usage output from argparse.
    old_stdout = sys.stdout # save stdout
    old_stderr = sys.stderr # save stderr
    sys.stdout = RedirectHelp(sys.stdout, helpStringReplacementPairs,
            initIndent, subsIndent, lineWidth) # redirect stdout to add postprocessor
    sys.stderr = RedirectHelp(sys.stderr, helpStringReplacementPairs,
            initIndent, subsIndent, lineWidth) # redirect stderr to add postprocessor

    # Run the actual argument-parsing operation via argparse.
    args = argparseParser.parse_args()

    # The argparse class has finished its argument-processing, so now no more
    # usage or help messages will be printed.  So restore stdout and stderr
    # to their usual settings, except with self-flushing added.
    sys.stdout = SelfFlushingOutstream(old_stdout)
    sys.stderr = SelfFlushingOutstream(old_stderr)

    return args

