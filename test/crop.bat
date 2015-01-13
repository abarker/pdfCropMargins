@echo off
REM This is a very simple batch file for Windows command terminals.  Most
REM settings in testing still have to be changed by hand.

set PROGPATH="e:\pdfCropMargins\project_root\pdfCropMargins\pdfCropMargins.py"
set PYEXE="python"

%PYEXE% %PROGPATH% -v %*

