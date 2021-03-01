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

This module contains all the function calls to external programs (Ghostscript
and pdftoppm).  All the system-specific information is also localized here.

Note for cleanup: This module creates a temp dir at time of initialization.

"""

from __future__ import print_function, division, absolute_import
import sys
import os
import subprocess
import tempfile
import glob
import shutil
import time
import contextlib
import platform
import threading

WINDOWS_GS64_GLOB = r"C:\Program Files*\gs\gs*\bin\gswin64c.exe"
WINDOWS_GS32_GLOB = r"C:\Program Files*\gs\gs*\bin\gswin32c.exe"

temp_file_prefix = "pdfCropMarginsTmp_"     # prefixed to all temporary filenames
temp_dir_prefix = "pdfCropMarginsTmpDir_"   # prefixed to all temporary dirnames

cygwin_full_path_prefix = "/cygdrive"

##
## Get info about the OS we're running on.
##

#  Get the version as a tuple of strings: (major, minor, patchlevel)
python_version = platform.python_version_tuple() # sys.version_info works too

# Get the system OS type from platform.system as a string such as "Linux",
# "Windows", or "CYGWIN*".  Note that os.name instead returns something like
# "nt" for Windows and "posix" for Linux and Cygwin.
system_os = platform.system()
if system_os[:6].lower() == "cygwin":
    system_os = "Cygwin"

#system_os = "Windows" # Uncomment ONLY to test Windows on Linux with Wine.

# Find the number of bits the OS supports.
if sys.maxsize > 2**32:
    system_bits = 64 # Supposed to work on Macs, too.
else:
    system_bits = 32

# Executable paths for Ghostscript, one line for each system OS, with the
# system_os string followed by the 64 and 32 bit executable pathnames.  Will
# use the PATH for the system.  On 64 bit systems the 32 bit name is tried
# if the 64 bit one fails.
gs_executables = (
    ("Linux", "gs", "gs"),
    ("Cygwin", "gs", "gs"),
    ("Darwin", "gs", "gs"),
    ("Windows", "gswin64c.exe", "gswin32c.exe")
)
gs_executable = None # Will be set to the executable selected for the platform.

pdftoppm_executables = (
    ("Linux", "pdftoppm", "pdftoppm"),
    ("Cygwin", "pdftoppm", "pdftoppm"),
    ("Darwin", "pdftoppm", "pdftoppm"),
    ("Windows", "pdftoppm.exe", "pdftoppm.exe")
)
pdftoppm_executable = None # Will be set to the executable selected for the platform.
old_pdftoppm_version = False # Program will check the version and set this if true.

# To find the correct path on Windows from the registry, consider this
# http://stackoverflow.com/questions/18283574/programatically-locate-gswin32-exe


##
## General utility functions for paths and finding the directory path.
##

def get_directory_location():
    """Find the location of the directory where the module that runs this
    function is located.  An empty `directory_locator.py` file is assumed to be in
    the same directory as the module.  Note that there are other ways to do
    this, but this way seems reasonably robust and portable.  (As long as
    the directory is a package the import will always look at the current
    directory first.)

    The source-directory location is currently used to find the package data
    directories holding the Windows executables."""
    from . import directory_locator
    return get_canonical_absolue_expanded_dirname(directory_locator.__file__)

def get_expanded_path(path):
    """Expand the user ('~') or any shell variables in the path and return
    it."""
    return os.path.expandvars(os.path.expanduser(path))

def get_canonical_absolute_expanded_path(path):
    """Get the canonical form of the absolute path from a possibly relative path
    (which may have symlinks, etc.)"""
    return os.path.normcase(
               os.path.normpath(
                   os.path.realpath( # Remove any symbolic links.
                       os.path.abspath( # May not be needed with realpath; to be safe.
                           get_expanded_path(path)))))

def get_canonical_absolue_expanded_dirname(path):
    """Get the absolute directory name from a possibly relative path."""
    return os.path.dirname(get_canonical_absolute_expanded_path(path))

def samefile(path1, path2):
    """Test if paths refer to the same file or directory."""
    if system_os == "Linux" or system_os == "Cygwin":
        return os.path.samefile(path1, path2)
    return (get_canonical_absolute_expanded_path(path1) ==
            get_canonical_absolute_expanded_path(path2))

def get_parent_directory(path):
    """Like `os.path.dirname` except it returns the absolute name of the parent
    of the dirname directory.  No symbolic link expansion (os.path.realpath)
    or user expansion (os.path.expanduser) is done."""
    if not os.path.isdir(path):
        path = os.path.dirname(path)
    return os.path.abspath(os.path.join(path, os.path.pardir))

def glob_pathname(path, exact_num_args=False, windows_only=False):
    """Expands any globbing in `path` (Windows shells don't do it).

    The `path` parameter should be a single pathname possibly containing glob
    symbols. The argument `exact_num_args` can be set to an integer to check
    for an exact number of matching files.  If `window_only` is true and
    `system_os` is not Windows then a list containing `path` is returned
    unmodified.

    Returns a list of all the matching paths."""
    if windows_only and system_os != "Windows":
        return [path]
    globbed = glob.glob(path)
    if not globbed: # Empty list of matching paths.
        #print("\nWarning in pdfCropMargins: Any wildcards in the path\n   "
        #      + path + "\nfailed to expand; no matching glob.  Treating as "
        #      "literal.", file=sys.stderr)
        globbed = [path]
    if exact_num_args and len(globbed) != exact_num_args:
        print("\nError in pdfCropMargins: The wildcards in the path\n   {}"
              "\nexpand to the wrong number of files ({} instead of {})."
              .format(path, len(globbed), exact_num_args), file=sys.stderr)
        cleanup_and_exit(1)
    return globbed

def convert_windows_path_to_cygwin(path):
    """Convert a Windows path to a Cygwin path.  Just handles the basic case."""
    if len(path) > 2 and path[1] == ":" and path[2] == "\\":
        newpath = cygwin_full_path_prefix + "/" + path[0]
        if len(path) > 3:
            newpath += "/" + path[3:]
        path = newpath
    path = path.replace("\\", "/")
    return path

def get_temporary_filename(extension="", use_program_temp_dir=True):
    """Return the string for a temporary file with the given extension or
    suffix.  For a file extension like .pdf the dot should also be in the
    passed string.  Caller is expected to open and close it as necessary and
    call os.remove on it after finishing with it.  (Note the entire
    `program_temp_directory` will be deleted on cleanup.)"""
    dir_name = None # Uses the regular system temp dir if None.
    if use_program_temp_dir:
        dir_name = program_temp_directory
    tmp_output_file = tempfile.NamedTemporaryFile(delete=True,
                     prefix=temp_file_prefix, suffix=extension, dir=dir_name, mode="wb")
    tmp_output_filename = tmp_output_file.name
    tmp_output_file.close() # This deletes the file, too, but it is empty in this case.
    return tmp_output_filename


# The global directory that all temporary files are written to.  Other modules
# all use the definition from this module.  This makes it easy to clean up all
# the possibly large files, even on KeyboardInterrupt, by just deleting this
# directory.
program_temp_directory = None # Set by `create_temporary_directory`.

# Set up an environment variable so Ghostscript will use program_temp_directory
# for its temporary files (to be sure they get deleted).
gs_environment = os.environ.copy()
gs_environment["TMPDIR"] = None # Set by `create_temporary_directory`.

@contextlib.contextmanager
def create_temporary_directory():
    """Create and set the `program_temp_directory` temporary directory and return the
    name.  Cleanup on exit from the context manager."""
    global program_temp_directory
    program_temp_directory = tempfile.mkdtemp(prefix=temp_dir_prefix)
    gs_environment["TMPDIR"] = program_temp_directory

    try:
        yield program_temp_directory
    finally:
        uninterrupted_remove_program_temp_directory()
        program_temp_directory = None
        gs_environment["TMPDIR"] = None

def remove_program_temp_directory():
    """Remove the global temp directory and all its contents."""
    if program_temp_directory and os.path.exists(program_temp_directory):
        max_retries = 3
        curr_retries = 0
        time_between_retries = 1
        while True:
            try:
                shutil.rmtree(program_temp_directory)
                break
            except IOError:
                curr_retries += 1
                if curr_retries > max_retries:
                    raise # re-raise the exception
                time.sleep(time_between_retries)
            except:
                print("Cleaning up temp dir...", file=sys.stderr)
                raise

# This thread is setup outside the function below because an interrupt might
# occur during the thread's setup time.  Probably overkill, but it doesn't hurt.
t = threading.Thread(target=remove_program_temp_directory, args=())

def uninterrupted_remove_program_temp_directory():
    """Call the cleanup function `remove_program_temp_directory` as a thread
    so it is not halted by interrupts."""
    global t
    t.start()
    t.join()
    t = threading.Thread(target=remove_program_temp_directory, args=())

def cleanup_and_exit(exit_code, stack_frame=None):
    """Exit the program, after cleaning up the temporary directory.  The `stack_frame`
    argument is for when `signal.signal` calls the function.  The returned `exit_code`
    is the signal number."""
    uninterrupted_remove_program_temp_directory()
    if stack_frame is not None:
        print("\nThe process of pdf-crop-margins was killed by signal {}..."
                .format(exit_code), file=sys.stderr)
    sys.exit(exit_code)


# Set some additional variables that this module exposes to other modules.
program_code_directory = get_directory_location()
project_src_directory = get_parent_directory(program_code_directory)


##
## General utility functions for running external processes.
##

def get_external_subprocess_output(command_list, print_output=False, indent_string="",
                      split_lines=True, ignore_called_process_errors=False, env=None):
    """Run the command and arguments in the command_list.  Will search the system
    PATH.  Returns the output as a list of lines.   If print_output is True the
    output is echoed to stdout, indented (or otherwise prefixed) by indent_string.
    Waits for command completion.  Called process errors can be set to be
    ignored if necessary."""

    # Note ghostscript bounding box output writes to stderr!  So we need to
    # be sure to capture the stderr along with the stdout.

    print_output = False # Useful for debugging to set True.

    try:
        use_popen = True # Needs to be True to set ignore_called_process_errors True
        if use_popen: # Use lower-level Popen call.
            p = subprocess.Popen(command_list, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, env=env)
            output, errout = p.communicate()
            returncode = p.poll()
            if not ignore_called_process_errors and returncode != 0:
                raise subprocess.CalledProcessError(returncode, command_list,
                                                    output=output)
        else: # Use a check_output call.
            # Note this does not work correctly if shell=True.
            output = subprocess.check_output(command_list, stderr=subprocess.STDOUT,
                                             shell=False, env=env)
    except:
        from .main_pdfCropMargins import args
        if args.verbose:
            print("\nException when trying to run this subprocess"
                  " command:\n   {}".format(command_list), file=sys.stderr)
        raise

    output = output.decode("utf-8")

    if split_lines or print_output:
        split_output = output.splitlines()
    if split_lines:
        output = split_output
    if print_output:
        print()
        for line in split_output:
            print(indent_string + line)
        sys.stdout.flush()
    return output

def call_external_subprocess(command_list, stdin_filename=None, stdout_filename=None,
                             stderr_filename=None, env=None):
    """Run the command and arguments in the command_list.  Will search the system
    PATH for commands to execute, but no shell is started.  Redirects any selected
    outputs to the given filename.  Waits for command completion."""
    stdin = open(stdin_filename, "r") if stdin_filename else None
    stdout = open(stdout_filename, "w") if stdout_filename else None
    stderr = open(stderr_filename, "w") if stderr_filename else None

    subprocess.check_call(command_list, stdin=stdin, stdout=stdout, stderr=stderr,
                          env=env)

    if stdin_filename:
        stdin.close()
    if stdout_filename:
        stdout.close()
    if stderr_filename:
        stderr.close()

def run_external_subprocess_in_background(command_list, env=None):
    """Runs the command and arguments in the list as a background process."""
    if system_os == "Windows":
        DETACHED_PROCESS = 0x00000008
        p = subprocess.Popen(command_list, shell=False, stdin=None, stdout=None,
                stderr=None, close_fds=True, creationflags=DETACHED_PROCESS, env=env)
    else:
        p = subprocess.Popen(command_list, shell=False, stdin=None, stdout=None,
                stderr=None, close_fds=True, env=env)
    return p # ignore the returned process if not needed

##
## Functions to find and test whether an external program is there and runs.
##

def set_gs_executable_to_string(gs_executable_path):
    """Used to simply set the value to whatever the user asks for.  The path
    is not tested first, and takes priority over all other settings."""
    # Maybe test run these, too, at some point.
    global gs_executable
    gs_executable = gs_executable_path

def init_and_test_gs_executable(exit_on_fail=False):
    """Find a Ghostscript executable and test it.  If a good one is found, set
    this module's global gs_executable variable to that path and return that
    path.  Otherwise return None.  Any path string set from the command line
    gets priority, and is not tested."""

    global gs_executable
    if gs_executable:
        return gs_executable # Has already been set to a path.

    # First try basic names against the PATH.
    gs_executable = find_and_test_executable(gs_executables, ["-dSAFER", "-v"], "Ghostscript")

    # If that fails, on Windows or Cygwin look in the 'Program Files' gs directory for it.
    if not gs_executable and (system_os == "Windows" or system_os == "Cygwin"):
        gs64 = glob.glob(WINDOWS_GS64_GLOB)
        if gs64:
            gs64 = gs64[0] # just take the first one for now
        else:
            gs64 = ""
        gs32 = glob.glob(WINDOWS_GS32_GLOB)
        if gs32:
            gs32 = gs32[0] # just take the first one for now
        else:
            gs32 = ""
        gs_execs = (("Windows", gs64, gs32), ("Cygwin",
                                              convert_windows_path_to_cygwin(gs64),
                                              convert_windows_path_to_cygwin(gs32)))
        gs_executable = find_and_test_executable(gs_execs,
                                                 ["-dSAFER", "-v"], "Ghostscript")

    if exit_on_fail and not gs_executable:
        print("Error in pdfCropMargins (detected in external_program_calls.py):"
              "\nNo Ghostscript executable was found.  Be sure your PATH is"
              "\nset properly.  You can use the `--ghostscriptPath` option to"
              "\nexplicitly set the path from the command line.", file=sys.stderr)
        cleanup_and_exit(1)

    return gs_executable

def set_pdftoppm_executable_to_string(pdftoppm_executable_path):
    """Used to simply set the value to whatever the user asks for.  The path
    is not tested first, and takes priority over all other settings."""
    # Maybe test run these, too, at some point.
    global pdftoppm_executable
    pdftoppm_executable = pdftoppm_executable_path

def init_and_test_pdftoppm_executable(prefer_local=False, exit_on_fail=False):
    """Find a pdftoppm executable and test it.  If a good one is found, set
    this module's global pdftoppm_executable variable to that path and return
    that string.  Otherwise return None.  Any path string set from the
    command line gets priority, and is not tested."""
    ignore_called_process_errors = False

    global pdftoppm_executable
    if pdftoppm_executable:
        return pdftoppm_executable # Has already been set to a path.

    pdftoppm_executable = find_and_test_executable(
                              pdftoppm_executables, ["-v"], "pdftoppm",
                              ignore_called_process_errors=ignore_called_process_errors)

    # If we're on Windows and either no pdftoppm was found or prefer_local was
    # specified then use the local pdftoppm.exe distributed with the project.
    # The local pdftoppm.exe can be tested on Linux with Wine.  Just hardcode
    # the system type to "Windows" and it automatically runs Wine on the exe.
    if prefer_local or (not pdftoppm_executable and system_os == "Windows"):
        if not prefer_local:
            print("\nWarning from pdfCropMargins: No system pdftoppm was found."
                  "\nReverting to an older, locally-packaged executable.  To silence"
                  "\nthis warning use the '--pdftoppmLocal' (or '-pdl') flag.",
                  file=sys.stderr)

        # NOTE: When updating xpdf version, change here and ALSO in setup.py, near top.
        path = os.path.join(project_src_directory, "pdfCropMargins",
                                                   "pdftoppm_windows_local",
                                                   "xpdf_tools_win_4_01_01")

        # Paths to the package_data Windows executables, made part of the package
        # with __init__.py files.
        pdftoppm_executable32 = os.path.join(path, "bin32", "pdftoppm.exe")
        pdftoppm_executable64 = os.path.join(path, "bin64", "pdftoppm.exe")
        # Cygwin is not needed below for now, but left in case something gets fixed
        # to allow the local version to run from there.
        pdftoppm_local_execs = (("Windows", pdftoppm_executable64, pdftoppm_executable32),
                                ("Cygwin",  pdftoppm_executable64, pdftoppm_executable32),)

        if not (os.path.exists(pdftoppm_executable32) and
                    os.path.exists(pdftoppm_executable64)):
            print("Error in pdfCropMargins: The locally packaged executable files were"
                  " not found.", file=sys.stderr)
            if exit_on_fail:
                cleanup_and_exit(1)

        ignore_called_process_errors = True # Local Windows pdftoppm returns code 99 but works.
        local_pdftoppm_executable = find_and_test_executable(
                              pdftoppm_local_execs, ["-v"], "pdftoppm",
                              ignore_called_process_errors=ignore_called_process_errors)
        if not local_pdftoppm_executable:
            print("\nWarning from pdfCropMargins: The local pdftoppm.exe program failed"
                  "\nto execute correctly or was not found (see additional error"
                  " message if not found).", file=sys.stderr)
        else:
            pdftoppm_executable = local_pdftoppm_executable

    if exit_on_fail and not pdftoppm_executable:
        print("Error in pdfCropMargins (detected in external_program_calls.py):"
              "\nNo pdftoppm executable was found.  Be sure your PATH is set"
              "\ncorrectly.  You can explicitly set the path from the command"
              "\nline with the `--pdftoppmPath` option.", file=sys.stderr)
        cleanup_and_exit(1)

    if pdftoppm_executable: # Found a version of pdftoppm, see if it's ancient or recent.
        cmd = [pdftoppm_executable, "--help"]
        run_output = get_external_subprocess_output(cmd, split_lines=False,
                               ignore_called_process_errors=ignore_called_process_errors)
        if not "-singlefile " in run_output or not "-rx " in run_output:
            global old_pdftoppm_version
            old_pdftoppm_version = True
    return pdftoppm_executable

def find_and_test_executable(executables, argument_list, string_to_look_for,
                          ignore_called_process_errors=False):
    """Try to run the executable for the current system with the given arguments
    and look in the output for the given test string.  The executables argument
    should be a tuple of tuples.  The internal tuples should be 3-tuples
    containing the platform.system() value ("Windows" or "Linux") followed by
    the 64 bit executable for that system, followed by the 32 bit executable for
    that system.  For example,
       (("Windows", "gswin64c.exe", "gswin32c.exe"),)
    Note that the paths can be full paths or relative commands to be run with
    respect to the relevant PATH environment variable.  On 64 bit machines the
    32 bit version is always tried if the 64 bit version fails.  Returns the
    working executable name for the system, or the None if both fail.  Ignores
    empty executable strings."""
    for system_paths in executables:
        if system_paths[0] != system_os:
            continue
        executable_paths = [system_paths[1], system_paths[2]]
        if system_bits == 32:
            del executable_paths[0] # 64 bit won't run
        for executable_path in executable_paths:
            if not executable_path:
                continue # ignore empty strings
            run_command_list = [executable_path] + argument_list
            try:
                run_output = get_external_subprocess_output(run_command_list,
                              split_lines=False,
                              ignore_called_process_errors=ignore_called_process_errors)
                if string_to_look_for in run_output:
                    return executable_path
            except (subprocess.CalledProcessError, OSError, IOError) as e:
                # OSError if it isn't found, CalledProcessError if it runs but returns
                # fail.
                pass
        return None
    return None


##
## Functions that call Ghostscript to fix PDFs or get bounding boxes.
##

def fix_pdf_with_ghostscript_to_tmp_file(input_doc_fname):
    """Attempt to fix a bad PDF file with a Ghostscript command, writing the output
    PDF to a temporary file and returning the filename.  Caller is responsible for
    deleting the file (but it is created in the temp directory)."""
    if not gs_executable:
        init_and_test_gs_executable(exit_on_fail=True)

    temp_file_name = get_temporary_filename(extension=".pdf")
    gs_run_command = [gs_executable, "-dSAFER", "-o", temp_file_name,
                    "-dPDFSETTINGS=/prepress", "-sDEVICE=pdfwrite", input_doc_fname]
    try:
        gs_output = get_external_subprocess_output(gs_run_command, print_output=True,
                                             indent_string="   ", env=gs_environment)
    except subprocess.CalledProcessError:
        print("\nError in pdfCropMargins:  Ghostscript returned a non-zero exit"
              "\nstatus when attempting to fix the file:\n   ", input_doc_fname,
              file=sys.stderr)
        cleanup_and_exit(1)
    except UnicodeDecodeError:
        print("\nWarning in pdfCropMargins:  In attempting to repair the PDF file"
              "\nGhostscript produced a message containing characters which cannot"
              "\nbe decoded by the 'utf-8' codec.  Ignoring and hoping for the best.",
              file=sys.stderr)
    return temp_file_name

def get_bounding_box_list_ghostscript(input_doc_fname, res_x, res_y, full_page_box):
    """Call Ghostscript to get the bounding box list.  Cannot set a threshold
    with this method."""
    if not gs_executable:
        init_and_test_gs_executable(exit_on_fail=True)

    res = "{}x{}".format(res_x, res_y)
    box_arg = "-dUseMediaBox" # should be default, but set anyway
    if "c" in full_page_box: box_arg = "-dUseCropBox"
    if "t" in full_page_box: box_arg = "-dUseTrimBox"
    if "a" in full_page_box: box_arg = "-dUseArtBox"
    if "b" in full_page_box: box_arg = "-dUseBleedBox" # may not be defined in gs

    gs_run_command = [gs_executable, "-dSAFER", "-dNOPAUSE", "-dBATCH", "-sDEVICE=bbox",
                    box_arg, "-r"+res, input_doc_fname]

    # Set printOutput to True for debugging or extra-verbose with Ghostscript's output.
    # Note Ghostscript writes the data to stderr, so the command below must capture it.
    try:
        gs_output = get_external_subprocess_output(gs_run_command,
                          print_output=False, indent_string="   ", env=gs_environment)
    except UnicodeDecodeError:
        print("\nError in pdfCropMargins:  In attempting to get the bounding boxes"
              "\nGhostscript encountered characters which cannot be decoded by the"
              "\n'utf-8' codec.",
              file=sys.stderr)
        cleanup_and_exit(1)

    bounding_box_list = []
    for line in gs_output:
        split_line = line.split()
        if split_line and split_line[0] == r"%%HiResBoundingBox:":
            del split_line[0]
            if len(split_line) != 4:
                print("\nWarning from pdfCropMargins: Ignoring this unparsable line"
                      "\nwhen finding the bounding boxes with Ghostscript:",
                      line, "\n", file=sys.stderr)
                continue
            # Note gs reports values in order left, bottom, right, top,
            # i.e., lower left point followed by top right point.
            bounding_box_list.append([float(bbox_val) for bbox_val in split_line])

    if not bounding_box_list:
        print("\nError in pdfCropMargins: Ghostscript failed to find any bounding"
              "\nboxes in the document.", file=sys.stderr)
        cleanup_and_exit(1)
    return bounding_box_list

def render_pdf_file_to_image_files_pdftoppm_ppm(pdf_file_name, root_output_file_path,
                                           res_x=150, res_y=150, extra_args=None):
    """Use the pdftoppm program to render a PDF file to .png images.  The
    root_output_file_path is prepended to all the output files, which have numbers
    and extensions added.  Extra arguments can be passed as a list in extra_args.
    Return the command output."""
    if extra_args is None:
        extra_args = []

    if not pdftoppm_executable:
        init_and_test_pdftoppm_executable(prefer_local=False, exit_on_fail=True)

    if old_pdftoppm_version:
        # We only have -r, not -rx and -ry.
        command = [pdftoppm_executable] + extra_args + ["-r", res_x, pdf_file_name,
                                              root_output_file_path]
    else:
        command = [pdftoppm_executable] + extra_args + ["-rx", res_x, "-ry", res_y,
                                              pdf_file_name, root_output_file_path]
    comm_output = get_external_subprocess_output(command)
    return comm_output

def render_pdf_file_to_image_files_pdftoppm_pgm(pdf_file_name, root_output_file_path,
                                           res_x=150, res_y=150):
    """Same as renderPdfFileToImageFile_pdftoppm_ppm but with -gray option for pgm."""

    comm_output = render_pdf_file_to_image_files_pdftoppm_ppm(pdf_file_name,
                                        root_output_file_path, res_x, res_y, ["-gray"])
    return comm_output

def render_pdf_file_to_image_files_ghostscript_png(pdf_file_name,
                                                    root_output_file_path,
                                                    res_x=150, res_y=150):
    """Use Ghostscript to render a PDF file to .png images.  The `root_output_file_path`
    is prepended to all the output files, which have numbers and extensions added.
    Return the command output."""
    # For gs commands see
    # http://ghostscript.com/doc/current/Devices.htm#File_formats
    # http://ghostscript.com/doc/current/Devices.htm#PNG
    if not gs_executable: init_and_test_gs_executable(exit_on_fail=True)
    command = [gs_executable, "-dBATCH", "-dNOPAUSE", "-sDEVICE=pnggray",
               "-r"+res_x+"x"+res_y, "-sOutputFile="+root_output_file_path+"-%06d.png",
               pdf_file_name]
    comm_output = get_external_subprocess_output(command, env=gs_environment)
    return comm_output

def render_pdf_file_to_image_files_ghostscript_bmp(pdf_file_name,
                                                    root_output_file_path,
                                                    res_x=150, res_y=150):
    """Use Ghostscript to render a PDF file to .bmp images.  The `root_output_file_path`
    is prepended to all the output files, which have numbers and extensions added.
    Return the command output."""
    # For gs commands see
    # http://ghostscript.com/doc/current/Devices.htm#File_formats
    # http://ghostscript.com/doc/current/Devices.htm#BMP
    # These are the BMP devices:
    #    bmpmono bmpgray bmpsep1 bmpsep8 bmp16 bmp256 bmp16m bmp32b
    if not gs_executable: init_and_test_gs_executable(exit_on_fail=True)
    command = [gs_executable, "-dBATCH", "-dNOPAUSE", "-sDEVICE=bmpgray",
               "-r"+res_x+"x"+res_y, "-sOutputFile="+root_output_file_path+"-%06d.bmp",
               pdf_file_name]
    comm_output = get_external_subprocess_output(command, env=gs_environment)
    return comm_output


##
## Function to run a previewing program on a PDF file.
##

def show_preview(viewer_path, pdf_file_name):
    """Run the PDF viewer at the path viewer_path on the file pdf_file_name."""
    try:
        cmd = [viewer_path, pdf_file_name]
        run_external_subprocess_in_background(cmd)
    except (subprocess.CalledProcessError, OSError, IOError) as e:
        print("\nWarning from pdfCropMargins: The argument to the '--viewer' option:"
              "\n   ", viewer_path, "\nwas not found or failed to execute correctly.\n",
              file=sys.stderr)
    return

