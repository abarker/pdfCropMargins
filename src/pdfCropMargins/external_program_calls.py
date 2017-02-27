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

This module contains all the function calls to external programs (Ghostscript
and pdftoppm).  All the system-specific information is also localized here.
Note for cleanup that this module creates a temp dir at time of initialization.

"""

from __future__ import print_function, division
import sys
import os
import subprocess
import tempfile
import glob
import shutil
import time

tempFilePrefix = "pdfCropMarginsTmp_"     # prefixed to all temporary filenames
tempDirPrefix = "pdfCropMarginsTmpDir_"   # prefixed to all temporary dirnames

cygwinFullPathPrefix = "/cygdrive"

##
## Get info about the OS we're running on.
##

import platform

#  Get the version as a tuple of strings: (major, minor, patchlevel)
pythonVersion = platform.python_version_tuple() # sys.version_info works too

# Get the system OS type from platform.system as a string such as "Linux",
# "Windows", or "CYGWIN*".  Note that os.name instead returns something like
# "nt" for Windows and "posix" for Linux and Cygwin.
systemOs = platform.system()
if systemOs[:6].lower() == "cygwin":
    systemOs = "Cygwin"

#systemOs = "Windows" # Uncomment ONLY to test Windows on Linux with Wine.

# Find the number of bits the OS supports.
if sys.maxsize > 2**32: systemBits = 64 # Supposed to work on Macs, too.
else: systemBits = 32

# Executable paths for Ghostscript, one line for each system OS, with the
# systemOs string followed by the 32 and 64 bit executable pathnames.  Will
# use the PATH for the system.
gsExecutables = (
    ("Linux", "gs", "gs"),
    ("Cygwin", "gs", "gs"),
    ("Windows", "gswin64c.exe", "gswin32c.exe")
)
gsExecutable = None # Will be set to the executable selected for the platform.

pdftoppmExecutables = (
    ("Linux", "pdftoppm", "pdftoppm"),
    ("Cygwin", "pdftoppm", "pdftoppm"),
    ("Windows", "pdftoppm.exe", "pdftoppm.exe")
)
pdftoppmExecutable = None # Will be set to the executable selected for the platform.
oldPdftoppmVersion = False # Program will check the version and set this if true.

# To find the correct path on Windows from the registry, consider this
# http://stackoverflow.com/questions/18283574/programatically-locate-gswin32-exe


##
## General utility functions for paths and finding the directory path.
##


def getTemporaryFilename(extension="", useProgramTempDir=True):
    """Return the string for a temporary file with the given extension or suffix.  For a
    file extension like .pdf the dot should also be in the passed string.  Caller is
    expected to open and close it as necessary and call os.remove on it after
    finishing with it.  (Note the entire programTempDir will be deleted on cleanup.)"""
    dirName = None # uses the regular system temp dir if None
    if useProgramTempDir: dirName = programTempDirectory
    tmpOutputFile = tempfile.NamedTemporaryFile(
          delete=False, prefix=tempFilePrefix, suffix=extension, dir=dirName, mode="wb")
    tmpOutputFile.close() # this deletes the file, too, but it is empty in this case
    return tmpOutputFile.name


def getTemporaryDirectory():
    """Create a temporary directory and return the name.  The caller is responsible
    for deleting it (e.g., with shutil.rmtree) after using it."""
    return tempfile.mkdtemp(prefix=tempDirPrefix)


def getDirectoryLocation():
    """Find the location of the directory where the module that runs this
    function is located.  An empty directory_locator.py file is assumed to be in
    the same directory as the module.  Note that there are other ways to do
    this, but this way seems reasonably robust and portable.  (As long as
    the directory is a package the import will always look at the current
    directory first.)"""
    from . import directory_locator
    return getCanonicalAbsolueExpandedDirname(directory_locator.__file__)


def getCanonicalAbsoluteExpandedPath(path):
    """Get the canonical form of the absolute path from a possibly relative path
    (which may have symlinks, etc.)"""
    return os.path.normcase(
               os.path.normpath(
                   os.path.realpath( # remove any symbolic links
                       os.path.abspath( # may not be needed with realpath, to be safe
                           os.path.expanduser(path)))))


def getCanonicalAbsolueExpandedDirname(path):
    """Get the absolute directory name from a possibly relative path."""
    return os.path.dirname(getCanonicalAbsoluteExpandedPath(path))


def samefile(path1, path2):
    """Test if paths refer to the same file or directory."""
    if systemOs == "Linux" or systemOs == "Cygwin":
        return os.path.samefile(path1, path2)
    return (getCanonicalAbsoluteExpandedPath(path1) ==
            getCanonicalAbsoluteExpandedPath(path2))


def getParentDirectory(path):
    """Like os.path.dirname except it returns the absolute name of the parent
    of the dirname directory.  No symbolic link expansion (os.path.realpath)
    or user expansion (os.path.expanduser) is done."""
    if not os.path.isdir(path): path = os.path.dirname(path)
    return os.path.abspath(os.path.join(path, os.path.pardir))


def globIfWindowsOs(path, exactNumArgs=False):
    """Expands any globbing if systemOs is Windows (DOS doesn't do it).  The
    argument exactNumFiles can be set to an integer to check for an exact
    number of matching files.  Returns a list."""
    if systemOs != "Windows": return [path]
    globbed = glob.glob(path)
    if not globbed:
        print("\nWarning in pdfCropMargins: The wildcards in the path\n   "
              + path + "\nfailed to expand.  Treating as literal.",
              file=sys.stderr)
        globbed = [path]
    if exactNumArgs and len(globbed) != exactNumArgs:
        print("\nError in pdfCropMargins: The wildcards in the path\n   "
              + path + "\nexpand to the wrong number of files.",
              file=sys.stderr)
        cleanupAndExit(1)
    return globbed


def convertWindowsPathToCygwin(path):
    """Convert a Windows path to a Cygwin path.  Just handles the basic case."""
    if len(path) > 2 and path[1] == ":" and path[2] == "\\":
        newpath = cygwinFullPathPrefix + "/" + path[0]
        if len(path) > 3: newpath += "/" + path[3:]
        path = newpath
    path = path.replace("\\", "/")
    return path


# Set some additional variables that this module exposes to other modules.
programCodeDirectory = getDirectoryLocation()
projectSrcDirectory = getParentDirectory(programCodeDirectory)

# The global directory that all temporary files are written to.  Other modules
# all use the definition from this module.  This makes it easy to clean up all
# the possibly large files, even on KeyboardInterrupt, by just deleting this
# directory.
programTempDirectory = getTemporaryDirectory()

# Set up an environment variable so Ghostscript will use programTempDirectory
# for its temporary files (to be sure they get deleted).
gsEnvironment = os.environ.copy()
gsEnvironment["TMPDIR"] = programTempDirectory


def removeProgramTempDirectory():
    """Remove the global temp directory and all its contents."""
    if os.path.exists(programTempDirectory):
        maxRetries = 3
        currRetries = 0
        timeBetweenRetries = 1
        while True:
            try:
                shutil.rmtree(programTempDirectory)
                break
            except IOError:
                currRetries += 1
                if currRetries > maxRetries: raise # re-raise the exception
                time.sleep(timeBetweenRetries)
    return


def cleanupAndExit(exitCode):
    """Exit the program, after cleaning up the temporary directory."""
    removeProgramTempDirectory()
    sys.exit(exitCode)
    return


def which(program):
    """This function is for possible future reference and modification, from
    stackexchange.  Not currently used."""
    # import os # already imported

    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None


##
## General utility functions for running external processes.
##


def getExternalSubprocessOutput(commandList, printOutput=False, indentString="",
                      splitLines=True, ignoreCalledProcessErrors=False, env=None):
    """Run the command and arguments in the commandList.  Will search the system
    PATH.  Returns the output as a list of lines.   If printOutput is True the
    output is echoed to stdout, indented (or otherwise prefixed) by indentString.
    Waits for command completion.  Called process errors can be set to be
    ignored if necessary."""

    # Note ghostscript bounding box output writes to stderr!  So we need to
    # be sure to capture the stderr along with the stdout.

    printOutput = False # Useful for debugging to set True.

    usePopen = True # Needs to be True to set ignoreCalledProcessErrors True
    if usePopen: # Use lower-level Popen call.
        p = subprocess.Popen(commandList, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, env=env)
        output, errout = p.communicate()
        returncode = p.poll()
        if not ignoreCalledProcessErrors and returncode != 0:
            raise subprocess.CalledProcessError(returncode, commandList, output=output)
    else: # Use a check_output call.
        # Note this does not work correctly if shell=True.
        output = subprocess.check_output(commandList, stderr=subprocess.STDOUT,
                                         shell=False, env=env)

    output = output.decode("utf-8")

    if splitLines or printOutput:
        splitOutput = output.splitlines()
    if splitLines:
        output = splitOutput
    if printOutput:
        print()
        for line in splitOutput:
            print(indentString + line)
        sys.stdout.flush()
    return output


def callExternalSubprocess(commandList,
                           stdinFilename=None, stdoutFilename=None, stderrFilename=None,
                           env=None):
    """Run the command and arguments in the commandList.  Will search the system
    PATH for commands to execute, but no shell is started.  Redirects any selected
    outputs to the given filename.  Waits for command completion."""

    if stdinFilename: stdin = open(stdinFilename, "r")
    else: stdin = None
    if stdoutFilename: stdout = open(stdoutFilename, "w")
    else: stdout = None
    if stderrFilename: stderr = open(stderrFilename, "w")
    else: stderr = None

    subprocess.check_call(commandList, stdin=stdin, stdout=stdout, stderr=stderr,
                          env=env)

    if stdinFilename: stdin.close()
    if stdoutFilename: stdout.close()
    if stderrFilename: stderr.close()

    # The older way to do the above with os.system is below, just for reference.
    # command = " ".join(commandList)
    # if stdinFilename: command += " < " + stdinFilename
    # if stdoutFilename: command += " > " + stdoutFilename
    # if stderrFilename: command += " 2> " + stderrFilename
    # os.system(command)
    return


def runExternalSubprocessInBackground(commandList, env=None):
    """Runs the command and arguments in the list as a background process."""
    if systemOs == "Windows":
        DETACHED_PROCESS = 0x00000008
        p = subprocess.Popen(commandList, shell=False, stdin=None, stdout=None,
                stderr=None, close_fds=True, creationflags=DETACHED_PROCESS, env=env)
    else:
        p = subprocess.Popen(commandList, shell=False, stdin=None, stdout=None,
                stderr=None, close_fds=True, env=env)
    return p # ignore the returned process if not needed


##
## Run a program in Python with a time limit (experimental, not currently used).
##


from multiprocessing import Process, Queue


def my_function(name): # debug test
    print("name is", name)
    time.sleep(7)
    print("afterward name is", name)
    return


def functionCallWithTimeout(funName, funArgs, secs=5):
    """Run a Python function with a timeout.  No interprocess communication or
    return values are handled.  Setting secs to 0 gives infinite timeout."""
    p = Process(target=funName, args=tuple(funArgs))
    p.start()
    currSecs = 0
    noTimeout = False
    if secs == 0: noTimeout = True
    else: timeout = secs
    while p.is_alive() and not noTimeout:
        if currSecs > timeout:
            print("Process time has exceeded timeout, terminating it.")
            p.terminate()
            return False
        time.sleep(0.1)
        currSecs += 0.1
    p.join() # Blocks if process hasn't terminated.
    return True

# debug test
#funcallWithTimeout(my_function, ["bob"])
#cleanupAndExit(0)


##
## Functions to find and test whether an external program is there and runs.
##


def setGsExecutableToString(gsExecutablePath):
    """Used to simply set the value to whatever the user asks for.  The path
    is not tested first, and takes priority over all other settings."""
    # Maybe test run these, too, at some point.
    global gsExecutable
    gsExecutable = gsExecutablePath
    return


def initAndTestGsExecutable(exitOnFail=False):
    """Find a Ghostscript executable and test it.  If a good one is found, set
    this module's global gsExecutable variable to that path and return that
    path.  Otherwise return None.  Any path string set from the command line
    gets priority, and is not tested."""

    global gsExecutable
    if gsExecutable: return gsExecutable # Has already been set to a path.

    # First try basic names against the PATH.
    gsExecutable = findAndTestExecutable(gsExecutables, ["-dSAFER", "-v"], "Ghostscript")

    # If that fails, on Windows or Cygwin look in the Program Files gs directory for it.
    if not gsExecutable and (systemOs == "Windows" or systemOs == "Cygwin"):
        # TODO maybe move these strings to top as module settable strings
        gs64 = glob.glob(r"C:\Program Files*\gs\gs*\bin\gswin64c.exe")
        if gs64: gs64 = gs64[0] # just take the first one for now
        else: gs64 = ""
        gs32 = glob.glob(r"C:\Program Files*\gs\gs*\bin\gswin32c.exe")
        if gs32: gs32 = gs32[0] # just take the first one for now
        else: gs32 = ""
        gsExecs = (("Windows", gs64, gs32), ("Cygwin",
                  convertWindowsPathToCygwin(gs64), convertWindowsPathToCygwin(gs32)))
        gsExecutable = findAndTestExecutable(gsExecs, ["-dSAFER", "-v"], "Ghostscript")

    if exitOnFail and not gsExecutable:
        print("Error in pdfCropMargins (detected in external_program_calls.py):"
              "\nNo Ghostscript executable was found.  Be sure your PATH is"
              "\nset properly.  You can use the `--ghostscriptPath` option to"
              "\nexplicitly set the path from the command line.", file=sys.stderr)
        cleanupAndExit(1)

    return gsExecutable


def setPdftoppmExecutableToString(pdftoppmExecutablePath):
    """Used to simply set the value to whatever the user asks for.  The path
    is not tested first, and takes priority over all other settings."""
    # Maybe test run these, too, at some point.
    global pdftoppmExecutable
    pdftoppmExecutable = pdftoppmExecutablePath
    return


def initAndTestPdftoppmExecutable(preferLocal=False, exitOnFail=False):
    """Find a pdftoppm executable and test it.  If a good one is found, set
    this module's global pdftoppmExecutable variable to that path and return
    that string.  Otherwise return None.  Any path string set from the
    command line gets priority, and is not tested."""

    ignoreCalledProcessErrors = False

    global pdftoppmExecutable
    if pdftoppmExecutable: return pdftoppmExecutable # Has already been set to a path.

    pdftoppmExecutable = findAndTestExecutable(
                              pdftoppmExecutables, ["-v"], "pdftoppm",
                              ignoreCalledProcessErrors=ignoreCalledProcessErrors)

    # If we're on Windows and either no pdftoppm was found or preferLocal was
    # specified then use the local pdftoppm.exe distributed with the project.
    # The local pdftoppm.exe can be tested on Linux with Wine.  Just hardcode
    # the system type to "Windows" and it automatically runs Wine on the exe.
    if preferLocal or (not pdftoppmExecutable and systemOs == "Windows"):
        if not preferLocal:
            print("\nWarning from pdfCropMargins: No system pdftoppm was found."
                  "\nReverting to an older, locally-packaged executable.  To silence"
                  "\nthis warning use the '--pdftoppmLocal' (or '-pdl') flag.",
                  file=sys.stderr)

        path = os.path.join(projectSrcDirectory, "pdfCropMargins", "pdftoppm_windows_local",
                                                                "xpdfbin_win_3_04")
        #path = os.path.join(projectSrcDirectory, "pdfCropMargins", "xpdfbin_win_3_04")

        pdftoppmExecutable32 = os.path.join(path, "bin32", "pdftoppm.exe")
        pdftoppmExecutable64 = os.path.join(path, "bin64", "pdftoppm.exe")
        # Cygwin is not needed below for now, but left in case something gets fixed
        # to allow the local version to run from there.
        pdftoppmLocalExecs = (("Windows", pdftoppmExecutable64, pdftoppmExecutable32),
                              ("Cygwin",  pdftoppmExecutable64, pdftoppmExecutable32),)

        if not (os.path.exists(pdftoppmExecutable32) and
                    os.path.exists(pdftoppmExecutable64)):
            print("Error in pdfCropMargins: The locally packaged executable files were"
                  " not found.", file=sys.stderr)
            if exitOnFail:
                cleanupAndExit(1)

        ignoreCalledProcessErrors = True # Local Windows pdftoppm returns code 99 but works.
        localPdftoppmExecutable = findAndTestExecutable(
                                   pdftoppmLocalExecs, ["-v"], "pdftoppm",
                                   ignoreCalledProcessErrors=ignoreCalledProcessErrors)
        if not localPdftoppmExecutable:
            print("\nWarning from pdfCropMargins: The local pdftoppm.exe program failed"
                  "\nto execute correctly or was not found.", file=sys.stderr)
        else:
            pdftoppmExecutable = localPdftoppmExecutable

    if exitOnFail and not pdftoppmExecutable:
        print("Error in pdfCropMargins (detected in external_program_calls.py):"
              "\nNo pdftoppm executable was found.  Be sure your PATH is set"
              "\ncorrectly.  You can explicitly set the path from the command"
              "\nline with the `--pdftoppmPath` option.", file=sys.stderr)
        cleanupAndExit(1)

    if pdftoppmExecutable: # Found a version of pdftoppm, see if it's ancient or recent.
        cmd = [pdftoppmExecutable, "--help"]
        runOutput = getExternalSubprocessOutput(cmd, splitLines=False,
                               ignoreCalledProcessErrors=ignoreCalledProcessErrors)
        if not "-singlefile " in runOutput or not "-rx " in runOutput:
            global oldPdftoppmVersion
            oldPdftoppmVersion = True
    return pdftoppmExecutable


def findAndTestExecutable(executables, argumentList, stringToLookFor,
                          ignoreCalledProcessErrors=False):
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

    for systemPaths in executables:
        if systemPaths[0] != systemOs: continue
        executablePaths = [systemPaths[1], systemPaths[2]]
        if systemBits == 32: del executablePaths[0] # 64 bit won't run
        for executablePath in executablePaths:
            if not executablePath: continue # ignore empty strings
            runCommandList = [executablePath] + argumentList
            try:
                runOutput = getExternalSubprocessOutput(runCommandList, splitLines=False,
                                       ignoreCalledProcessErrors=ignoreCalledProcessErrors)
                if stringToLookFor in runOutput:
                    return executablePath
            except (subprocess.CalledProcessError, OSError, IOError) as e:
                # OSError if it isn't found, CalledProcessError if it runs but returns
                # fail.
                pass
        return None
    return None


##
## Functions that call Ghostscript to fix PDFs or get bounding boxes.
##


def fixPdfWithGhostscriptToTmpFile(inputDocFname):
    """Attempt to fix a bad PDF file with a Ghostscript command, writing the output
    PDF to a temporary file and returning the filename.  Caller is responsible for
    deleting the file."""

    if not gsExecutable: initAndTestGsExecutable(exitOnFail=True)
    tempFileName = getTemporaryFilename(extension=".pdf")
    gsRunCommand = [gsExecutable, "-dSAFER", "-o", tempFileName,
                    "-dPDFSETTINGS=/prepress", "-sDEVICE=pdfwrite", inputDocFname]
    try:
        gsOutput = getExternalSubprocessOutput(gsRunCommand,
                              printOutput=True, indentString="   ", env=gsEnvironment)
    except subprocess.CalledProcessError:
        print("\nError in pdfCropMargins:  Ghostscript returned a non-zero exit"
              "\nstatus when attempting to fix the file:\n   ", inputDocFname,
              file=sys.stderr)
        cleanupAndExit(1)
    except UnicodeDecodeError:
        print("\nWarning in pdfCropMargins:  In attempting to repair the PDF file"
              "\nGhostscript produced a message containing characters which cannot"
              "\nbe decoded by the 'utf-8' codec.  Ignoring and hoping for the best.",
              file=sys.stderr)
    return tempFileName


def getBoundingBoxListGhostscript(inputDocFname, resX, resY, fullPageBox):
    """Call Ghostscript to get the bounding box list.  Cannot set a threshold
    with this method."""

    if not gsExecutable: initAndTestGsExecutable(exitOnFail=True)
    res = str(resX) + "x" + str(resY)
    boxArg = "-dUseMediaBox" # should be default, but set anyway
    if "c" in fullPageBox: boxArg = "-dUseCropBox"
    if "t" in fullPageBox: boxArg = "-dUseTrimBox"
    if "a" in fullPageBox: boxArg = "-dUseArtBox"
    if "b" in fullPageBox: boxArg = "-dUseBleedBox" # may not be defined in gs
    gsRunCommand = [gsExecutable, "-dSAFER", "-dNOPAUSE", "-dBATCH", "-sDEVICE=bbox",
                    boxArg, "-r"+res, inputDocFname]
    # Set printOutput to True for debugging or extra-verbose with Ghostscript's output.
    # Note Ghostscript writes the data to stderr, so the command below must capture it.
    try:
        gsOutput = getExternalSubprocessOutput(gsRunCommand,
                          printOutput=False, indentString="   ", env=gsEnvironment)
    except UnicodeDecodeError:
        print("\nError in pdfCropMargins:  In attempting to get the bounding boxes"
              "\nGhostscript encountered characters which cannot be decoded by the"
              "\n'utf-8' codec.",
              file=sys.stderr)
        cleanupAndExit(1)

    boundingBoxList = []
    for line in gsOutput:
        splitLine = line.split()
        if splitLine and splitLine[0] == r"%%HiResBoundingBox:":
            del splitLine[0]
            if len(splitLine) != 4:
                print("\nWarning from pdfCropMargins: Ignoring this unparsable line"
                      "\nwhen finding the bounding boxes with Ghostscript:",
                      line, "\n", file=sys.stderr)
                continue
            # Note gs reports values in order left, bottom, right, top,
            # i.e., lower left point followed by top right point.
            boundingBoxList.append([float(splitLine[0]),
                                    float(splitLine[1]),
                                    float(splitLine[2]),
                                    float(splitLine[3])])

    if not boundingBoxList:
        print("\nError in pdfCropMargins: Ghostscript failed to find any bounding"
              "\nboxes in the document.", file=sys.stderr)
        cleanupAndExit(1)
    return boundingBoxList


def renderPdfFileToImageFiles_pdftoppm_ppm(pdfFileName, rootOutputFilePath,
                                           resX=150, resY=150, extraArgs=None):
    """Use the pdftoppm program to render a PDF file to .png images.  The
    rootOutputFilePath is prepended to all the output files, which have numbers
    and extensions added.  Extra arguments can be passed as a list in extraArgs.
    Return the command output."""

    if extraArgs is None: extraArgs = []

    if not pdftoppmExecutable:
        initAndTestPdftoppmExecutable(preferLocal=False, exitOnFail=True)

    if oldPdftoppmVersion:
        # We only have -r, not -rx and -ry.
        command = [pdftoppmExecutable] + extraArgs + ["-r", resX, pdfFileName,
                                              rootOutputFilePath]
    else:
        command = [pdftoppmExecutable] + extraArgs + ["-rx", resX, "-ry", resY,
                                              pdfFileName, rootOutputFilePath]
    commOutput = getExternalSubprocessOutput(command)
    return commOutput


def renderPdfFileToImageFiles_pdftoppm_pgm(pdfFileName, rootOutputFilePath,
                                           resX=150, resY=150):
    """Same as renderPdfFileToImageFile_pdftoppm_ppm but with -gray option for pgm."""

    commOutput = renderPdfFileToImageFiles_pdftoppm_ppm(pdfFileName, rootOutputFilePath,
                                                        resX, resY, ["-gray"])
    return commOutput


def renderPdfFileToImageFiles_Ghostscript_png(pdfFileName, rootOutputFilePath,
                                              resX=150, resY=150):
    """Use Ghostscript to render a PDF file to .png images.  The rootOutputFilePath
    is prepended to all the output files, which have numbers and extensions added.
    Return the command output."""
    # For gs commands see
    # http://ghostscript.com/doc/current/Devices.htm#File_formats
    # http://ghostscript.com/doc/current/Devices.htm#PNG
    if not gsExecutable: initAndTestGsExecutable(exitOnFail=True)
    command = [gsExecutable, "-dBATCH", "-dNOPAUSE", "-sDEVICE=pnggray",
               "-r"+resX+"x"+resY, "-sOutputFile="+rootOutputFilePath+"-%06d.png",
               pdfFileName]
    commOutput = getExternalSubprocessOutput(command, env=gsEnvironment)
    return commOutput


def renderPdfFileToImageFiles_Ghostscript_bmp(pdfFileName, rootOutputFilePath,
                                              resX=150, resY=150):
    """Use Ghostscript to render a PDF file to .bmp images.  The rootOutputFilePath
    is prepended to all the output files, which have numbers and extensions added.
    Return the command output."""
    # For gs commands see
    # http://ghostscript.com/doc/current/Devices.htm#File_formats
    # http://ghostscript.com/doc/current/Devices.htm#BMP
    # These are the BMP devices:
    #    bmpmono bmpgray bmpsep1 bmpsep8 bmp16 bmp256 bmp16m bmp32b
    if not gsExecutable: initAndTestGsExecutable(exitOnFail=True)
    command = [gsExecutable, "-dBATCH", "-dNOPAUSE", "-sDEVICE=bmpgray",
               "-r"+resX+"x"+resY, "-sOutputFile="+rootOutputFilePath+"-%06d.bmp",
               pdfFileName]
    commOutput = getExternalSubprocessOutput(command, env=gsEnvironment)
    return commOutput


##
## Function to run a previewing program on a PDF file.
##


def showPreview(viewerPath, pdfFileName):
    """Run the PDF viewer at the path viewerPath on the file pdfFileName."""
    try:
        cmd = [viewerPath, pdfFileName]
        runExternalSubprocessInBackground(cmd)
    except (subprocess.CalledProcessError, OSError, IOError) as e:
        print("\nWarning from pdfCropMargins: The argument to the '--viewer' option:"
              "\n   ", viewerPath, "\nwas not found or failed to execute correctly.\n")
    return

