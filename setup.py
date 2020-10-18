# -*- encoding: utf-8 -*-
"""

A setuptools-based setup module.

See:
   https://packaging.python.org/en/latest/distributing.html

Docs on the setup function kwargs:
   https://packaging.python.org/distributing/#setup-args

"""

from __future__ import absolute_import, print_function
import glob
import os.path
from setuptools import setup, find_packages, Distribution
import codecs # Use a consistent encoding.
import shutil
import re

# Get the version data from the main __init__.py file.
with open(os.path.join("src", "pdfCropMargins", "__init__.py")) as f:
    __version__ = re.search(r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read()).group(1)

# To package external data, which includes an executable, the package_dir
# option tends to be better than the data_files option, which does not preserve
# the directory structure and puts the data in the wrong place for package data
# upon installation.  To use package_data all directory names must be valid
# package names, though, and you also need an __init__.py in each such
# directory and subdirectory.

# Paths to data files, relative to the main package directory.
path_to_copied_exe64 = os.path.join(
               "pdftoppm_windows_local", "xpdf_tools_win_4_01_01", "bin64", "pdftoppm.exe")
path_to_copied_exe32 = os.path.join(
               "pdftoppm_windows_local", "xpdf_tools_win_4_01_01", "bin32", "pdftoppm.exe")

package_dir = {"": "src"} # Note src isn't used in later dotted package paths, set here!
packages = find_packages("src") # Finds submodules (otherwise need explicit listing).
py_modules = [os.path.splitext(
                 os.path.basename(path))[0]
                     for path in glob.glob("src/*.py")] # Only non-pkg modules.

# Get the long description from the README.rst file.
current_dir = os.path.abspath(os.path.dirname(__file__))
with codecs.open(os.path.join(current_dir, "README.rst"), encoding="utf-8") as f:
    long_description = f.read()

install_requires = ["wheel",
                    "pillow>=7.1.0; python_version>='3.0.0'", # Security issues on older.
                    #"pillow>=6.2.2,<7.0.0; python_version<'3.0.0'", # Last supporting 2.7.
                    "PyPDF2"]

# A default extras group would be nice, to have 'lite' be a light version and 'gui' be
# the default, but not yet implemented: https://github.com/pypa/setuptools/issues/1139
extras_require={
                "gui": ["PySimpleGUI>=4.28.0;python_version>='3.0'",
                        "PySimpleGUI27>=2.4.1;python_version<'3.0'",
                        "typing;python_version<='3.4'", # PySimpleGUI27 on Python2 needs this.
                        "PyMuPDF>=1.16.17",],
                "mupdf": ["PyMuPDF>=1.16.17",],
                }

setup(
    name="pdfCropMargins",
    version=__version__, # <majorVersion>.<minorVersion>.<patch> format, (see PEP440)
    description="A command-line program to crop the margins of PDF files, with many options.",
    keywords=["pdf", "crop", "margins", "resize"],
    install_requires=install_requires,
    extras_require=extras_require,
    url="https://github.com/abarker/pdfCropMargins",
    entry_points = {
        "console_scripts": ["pdf-crop-margins = pdfCropMargins.pdfCropMargins:main"]
        },
    license="GPL",
    classifiers=[
        # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
        # Development Status: Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: Unix",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        # uncomment if you test on these interpreters:
        # "Programming Language :: Python :: Implementation :: IronPython",
        # "Programming Language :: Python :: Implementation :: Jython",
        # "Programming Language :: Python :: Implementation :: Stackless",
        "Topic :: Utilities",
    ],

    # Settings usually the same.
    author="Allen Barker",
    author_email="Allen.L.Barker@gmail.com",

    #include_package_data=True, # Not set True when package_data is set.
    package_data={"pdfCropMargins":[path_to_copied_exe32, path_to_copied_exe64]},
    zip_safe=False,

    # Automated stuff below
    long_description=long_description,
    packages=packages,
    package_dir=package_dir,
    py_modules=py_modules,
)


