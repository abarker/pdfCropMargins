"""

This module contains all the function calls to external programs (Ghostscript
and pdftoppm) and related functions.

"""

from __future__ import print_function, division
import sys, os, subprocess, tempfile

#
# Get info about the OS we're running on.
#

import platform
pythonVersion = platform.python_version_tuple() # sys.version_info[0] works too
systemOs = platform.system() # "Linux" or "Windows"; os.name works too
if sys.maxsize > 2**32: systemBits = 64 # Supposed to work on Macs, too.
else: systemBits = 32

# Executable paths for Ghostscript, one line for each system OS, with the
# systemOs string followed by the 32 and 64 bit executable pathnames.  Will
# use the PATH for the system.
gsExecutables = (
     ("Linux", "gs", "gs"),
     ("Windows", "GSWIN64C.EXE", "GSWIN32C.EXE")
     )
gsExecutable = None # Will be set to the executable selected for the platform.

pdftoppmExecutables = (
     ("Linux", "pdftoppm", "pdftoppm"),
     ("Windows", "pdftoppm.exe", "pdftoppm.exe")
     )
pdftoppmExecutable = None # Will be set to the executable selected for the platform.

# To find the correct path on Windows from the registry, consider this
# http://stackoverflow.com/questions/18283574/programatically-locate-gswin32-exe


def getExternalSubprocessOutput(commandList, printOutput=False, indentString="",
                                splitLines=True):
   """Run the command and arguments in the commandList.  Will search the system
   PATH.  Returns the output as a list of lines.   If printOutput is true the
   output is echoed to stdout, indented (or otherwise prefixed) by indentString."""
   # TODO do a try on the subprocess call, like in other place in this prog...
   output = subprocess.check_output(commandList, stderr=subprocess.STDOUT)
   output = output.decode("utf-8")
   if splitLines or printOutput: output = output.splitlines()
   if printOutput:
      print()
      for line in output:
         print(indentString + line)
      sys.stdout.flush()
   return output


def callExternalSubprocess(commandList, 
                  stdinFilename=None, stdoutFilename=None, stderrFilename=None):
   """Run the command and arguments in the commandList.  Will search the system
   PATH for commands to execute, but no shell is started.  Redirects any selected
   outputs to the given filename."""
   if stdinFilename: stdin = open(stdinFilename, "r")
   else: stdin = None
   if stdoutFilename: stdout = open(stdoutFilename, "w")
   else: stdout = None
   if stderrFilename: stderr = open(stderrFilename, "r")
   else: stderr = None

   subprocess.check_call(commandList, stdin=stdin, stdout=stdout, stderr=stderr)

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


def testGsExecutable():
   """Find a Ghostscript executable and test it.  If a good one is found, set
   this module's global gsExecutable variable to that path and return True.
   Otherwise return False."""
   global gsExecutable
   gsExecutable = testExecutable(gsExecutables, ["-dSAFER", "-v"], "Ghostscript")
   return not gsExecutable == ""

def testGsExecutableWithExit():
   """Same as testGsExecutable but exits with a message on failure."""
   if gsExecutable: return # has already been tested and set to a path
   if not testGsExecutable():
      print("Error in pdfCropMargins, detected in external_program_calls.py:"
            "\nNo Ghostscript executable was found.", file=sys.stderr)
      sys.exit(1)


def testPdftoppmExecutable():
   """Find a pdftoppm executable and test it.  If a good one is found, set
   this module's global pdftoppmExecutable variable to that path and return
   True.  Otherwise return False."""
   global pdftoppmExecutable
   pdftoppmExecutable = testExecutable(pdftoppmExecutables, ["-v"], "pdftoppm")
   # TODO just check here for failsafe local!  Can have an optional argument
   # to always prefer the local!
   return not pdftoppmExecutable == ""

def testPdftoppmExecutableWithExit():
   """Same as testPdftoppmExecutable but exits with a message on failure."""
   if pdftoppmExecutable: return # has already been tested and set to a path
   if not testPdftoppmExecutable():
      print("Error in pdfCropMargins, detected in external_program_calls.py:"
            "\nNo pdftoppm executable was found.", file=sys.stderr)
      sys.exit(1)


def testExecutable(executables, argumentList, stringToLookFor):
   """Try to run the executable for the current system with the given arguments
   and look in the output for the given test string.  The executables argument
   should be a tuple of tuples.  The internal tuples should be 3-tuples
   containing the platform.system() value ("Windows" or "Linux") followed by
   the 64 bit executable for that system, followed by the 32 bit executable for
   that system.  On 64 bit machines the 32 bit version is always tried if the
   64 bit version fails.  Returns the working executable name, or the empty
   string if both fail.  Ignores empty executable strings."""
   for systemPaths in executables:
      if systemPaths[0] != platform.system(): continue
      executablePaths = [systemPaths[1], systemPaths[2]]
      if systemBits == 32: del executablePaths[1]
      for executablePath in executablePaths:
         if not executablePath: continue
         runCommandList = [executablePath] + argumentList
         try:
            runOutput = getExternalSubprocessOutput(runCommandList, splitLines=False)
            if runOutput.find(stringToLookFor) != -1: return executablePath
         except (subprocess.CalledProcessError, OSError, IOError):
            # OSError if it isn't found, CalledProcessError if it runs but returns fail.
            pass
      return ""
   return ""


def fixPdfWithGhostscriptToTmpFile(inputDocFname):
   """Attempt to fix a bad PDF file with a Ghostscript command, writing the output
   PDF to a temporary file and returning the filename.  Caller is responsible for
   deleting the file."""
   testGsExecutableWithExit()
   fileObject = tempfile.NamedTemporaryFile(prefix="pdfCropMarginsTmp_", delete=False)
   fileObject.close()
   tempFileName = fileObject.name
   gsRunCommand = [gsExecutable, "-dSAFER", "-o", tempFileName,
         "-dPDFSETTINGS=/prepress", "-sDEVICE=pdfwrite", inputDocFname]
   gsOutput = getExternalSubprocessOutput(gsRunCommand, 
                                                printOutput=True, indentString="   ")
   return tempFileName


def getBoundingBoxListGhostscript(inputDocFname, resX, resY, fullPageBox):
   """Call Ghostscript to get the bounding box list.  Cannot set a threshold
   with this method."""

   testGsExecutableWithExit()
   res = str(resX) + "x" + str(resY)
   boxArg = "-dUseMediaBox"
   if "c" in fullPageBox: boxArg = "-dUseCropBox"
   if "t" in fullPageBox: boxArg = "-dUseTrimBox"
   if "a" in fullPageBox: boxArg = "-dUseArtBox"
   if "b" in fullPageBox: boxArg = "-dUseBleedBox" # may not be defined in gs
   gsRunCommand = [gsExecutable, "-dSAFER", "-dNOPAUSE", "-dBATCH", "-sDEVICE=bbox", 
         boxArg, "-r"+res, inputDocFname]
   # Set printOutput to True for debugging or extra verbose with Ghostscript's output.
   gsOutput = getExternalSubprocessOutput(gsRunCommand,
                                          printOutput=False, indentString="   ")
   boundingBoxList = []
   for line in gsOutput:
      line = line.split()
      if line[0] == r"%%HiResBoundingBox:":
         del line[0]
         # Note gs reports values in order left, bottom, right, top, or lower left
         # point followed by top right point.
         boundingBoxList.append( [ float(line[0]),
                                   float(line[1]),
                                   float(line[2]),
                                   float(line[3])] )
   return boundingBoxList


def getTemporaryFilename(extension=""):
   """Return the string for a temporary file with the given extension or suffix.  For a
   file extension like .pdf the dot should also be in the passed string.  Caller is
   expected to open and close it as necessary and call os.remove on it after
   finishing with it."""
   tmpOutputFile = tempfile.NamedTemporaryFile(delete=False,
         prefix="pdfCropMarginsTmpPdf_", suffix=extension, mode="wb")
   tmpOutputFile.close()
   return tmpOutputFile.name


def renderPdfFileToImageFile_pdftoppm_ppm(pdfFileName, imageFileName, resX=150, resY=150):
   # Note that if to include the imageFileName in the command itself you need to use
   # the root of the filename, i.e., without the extension.  So you can redirect to stdout.
   # Note that without -singlefile and stdout the program includes a number in filename.
   imageFileNameRoot, imageFileNameExtension = os.path.splitext(imageFileName)
   command = ["pdftoppm", "-rx", resX, "-ry", resY, "-singlefile", pdfFileName,
              imageFileNameRoot]
   getExternalSubprocessOutput(command, printOutput=False, indentString="   ")
   #command = ["pdftoppm", "-rx", resX, "-ry", resY, "-singlefile", pdfFileName]
   #callExternalSubprocess(command, stdoutFilename=imageFileName)
   return


def renderPdfFileToImageFile_pdftoppm_pgm(pdfFileName, imageFileName, resX=150, resY=150):
   # Same as renderPdfFileToImageFile_pdftoppm_ppm but with -gray option for pgm.
   imageFileNameRoot, imageFileNameExtension = os.path.splitext(imageFileName)
   command = ["pdftoppm", "-rx", resX, "-ry", resY, "-singlefile", "-gray", pdfFileName,
              imageFileNameRoot]
   getExternalSubprocessOutput(command, printOutput=False, indentString="   ")
   return


def renderPdfFileToImageFile_Ghostscript_png(pdfFileName, imageFileName, resX=150, resY=150):
   # For gs commands see http://ghostscript.com/doc/8.54/Use.htm
   testGsExecutableWithExit()
   command = [gsExecutable, "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=pnggray",
              "-r"+resX+"x"+resY, "-sOutputFile="+imageFileName, pdfFileName]
   # For extra-verbose output printOutput can be set True.
   getExternalSubprocessOutput(command, printOutput=False, indentString="  ")
   return 


