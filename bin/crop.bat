@echo off
REM Usage: crop <argumentsToPdfCropMargins>
REM
REM This is a very simple batch file for Windows command terminals.  Set the
REM path PROGPATH to the appropriate location on your system and copy this
REM script to your bin directory or somewhere else in your PATH.  If python
REM isn't in your PATH you will also need to set PYEXE to the full pathname for
REM running python.
REM
REM You can add any extra options that you always use in the final line where
REM the script is executed.  Currently the options -v, -u, -s, and -pf are
REM selected.

set PROGPATH="C:\INSERT_PATH_HERE\pdfCropMargins-master\src\pdfCropMargins"
set PYEXE="python"

%PYEXE% %PROGPATH% -v -u -s -pf %*

