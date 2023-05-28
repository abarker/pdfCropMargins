"""

Code that calls pyMuPDF.

=========================================================================

Some of this code is heavily modified from the GPL example/demo code found here:
https://github.com/PySimpleGUI/PySimpleGUI/blob/master/DemoPrograms/Demo_PDF_Viewer.py

Copyright (C) 2020 Allen Barker (Allen.L.Barker@gmail.com)
Source code site: https://github.com/abarker/pdfCropMargins

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

"""

#TODO
"""

https://www.phind.com/search?cache=8f133ae7-0754-494b-abc7-1ab6b670ed5e

write a python method to convert a pymupdf document into a pypdf2 documentreader
Answer

To convert a PyMuPDF document into a PyPDF2 PdfFileReader object, you can use
the following approach:

    Save the PyMuPDF document to a temporary file.
    Read the temporary file using PyPDF2 PdfFileReader.

Here's a Python method that performs the conversion:

This method takes a fitz.Document object as input and returns a
PyPDF2.PdfFileReader object. It creates a temporary file to store the PyMuPDF
document before reading it with PyPDF2.

Pros:

    Straightforward implementation
    Works with both libraries

Cons:

    Requires saving the document to a temporary file, which might impact performance
    May not preserve all features or formatting when converting between the two libraries

Keep in mind that PyMuPDF and PyPDF2 have different feature sets, so some
features or formatting might be lost during the conversion. If possible, it's
better to choose one library and stick with it throughout your project.

"""
import sys
import warnings
import copy
from . import external_program_calls as ex

has_mupdf = True

try: # Extra dependencies for the GUI version.  Make sure they are installed.
    with warnings.catch_warnings():
        #warnings.filterwarnings("ignore",category=DeprecationWarning)
        import fitz
        from fitz import Rect
        import os
        import tempfile # Maybe later write to the regular tmp dir...
        from PyPDF2 import PdfFileReader
    if not [int(i) for i in fitz.VersionBind.split(".")] >= [1, 16, 17]:
        has_mupdf = False
        MuPdfDocument = None

except ImportError:
    has_mupdf = False
    MuPdfDocument = None

def intersect_pdf_boxes(box1, box2, page):
    """Return the intersection of PDF-style boxes by converting to
    pymupdf and using its intersection function, then converting
    back."""
    box1_pymupdf = convert_box_pdf_to_pymupdf(box1, page)
    box2_pymupdf = convert_box_pdf_to_pymupdf(box2, page)
    intersection = box1_pymupdf.intersect(box2_pymupdf)
    return convert_box_pymupdf_to_pdf(intersection, page)

"""

original box:
bounding: 34 	 [127.0, 556.0, 534.0, 698.0]


xxxx Set mediabox back to this value:  Rect(0.0, 0.0, 612.0, 792.0)
xxxx Read this value back from mediabox, pymupdf format: Rect(0.0, 0.0, 612.0, 792.0)
transformation_matrix Matrix(1.0, 0.0, 0.0, -1.0, 0.0, 792.0)
xxxx Read this value back from mediabox, pdf format: Rect(0.0, 0.0, 612.0, 792.0)

	34	 [114.3, 500.4, 541.8, 707.4]
transformation_matrix Matrix(1.0, 0.0, 0.0, -1.0, 0.0, 792.0)

xxxxx Now setting mediabox to this cropped value: [114.3, 500.4, 541.8, 707.4]

xxxxx Reading back mediabox for the cropped value, pymupdf format: Rect(114.3, 84.6, 541.8, 291.6)
transformation_matrix Matrix(1.0, 0.0, 0.0, -1.0, -114.30000305175781, 291.6000061035156)

xxxxx Reading back mediabox for the cropped value, pdf format: Rect(228.60000610351562, 0.0, 656.0999755859375, 207.0)

===original below==========

Original full page sizes (rounded to 8 digits) in PDF format (lbrt):
	1   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	2   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	3   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	4   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	5   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	6   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	7   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	8   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	9   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	10   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	11   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	12   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	13   rot = 90  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	14   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	15   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	16   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	17   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	18   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	19   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	20   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	21   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	22   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	23   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	24   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	25   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	26   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	27   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	28   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	29   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	30   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	31   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	32   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	33   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]
	34   rot = 0  	 [0E-8, 0E-8, 612.00000000, 792.00000000]

The bounding boxes are:
	 1 	 [18.0, 101.0, 534.0, 732.0]
	 2 	 [131.0, 99.0, 535.0, 698.0]
	 3 	 [131.0, 134.0, 535.0, 698.0]
	 4 	 [131.0, 98.0, 535.0, 698.0]
	 5 	 [131.0, 107.0, 534.0, 698.0]
	 6 	 [131.0, 115.0, 534.0, 698.0]
	 7 	 [131.0, 103.0, 534.0, 698.0]
	 8 	 [131.0, 98.0, 534.0, 698.0]
	 9 	 [131.0, 217.0, 541.0, 698.0]
	 10 	 [131.0, 103.0, 535.0, 698.0]
	 11 	 [131.0, 99.0, 534.0, 698.0]
	 12 	 [131.0, 101.0, 535.0, 698.0]
	 13 	 [153.0, 75.0, 533.0, 698.0]
	 14 	 [131.0, 110.0, 535.0, 698.0]
	 15 	 [131.0, 101.0, 535.0, 698.0]
	 16 	 [131.0, 101.0, 534.0, 698.0]
	 17 	 [130.0, 99.0, 534.0, 698.0]
	 18 	 [131.0, 61.0, 514.0, 698.0]
	 19 	 [144.0, 111.0, 534.0, 698.0]
	 20 	 [130.0, 101.0, 535.0, 698.0]
	 21 	 [131.0, 99.0, 534.0, 698.0]
	 22 	 [131.0, 99.0, 535.0, 698.0]
	 23 	 [131.0, 101.0, 535.0, 698.0]
	 24 	 [131.0, 99.0, 535.0, 698.0]
	 25 	 [131.0, 104.0, 535.0, 698.0]
	 26 	 [131.0, 99.0, 535.0, 698.0]
	 27 	 [131.0, 99.0, 535.0, 698.0]
	 28 	 [131.0, 99.0, 534.0, 698.0]
	 29 	 [131.0, 99.0, 535.0, 698.0]
	 30 	 [131.0, 99.0, 535.0, 698.0]
	 31 	 [131.0, 99.0, 535.0, 698.0]
	 32 	 [128.0, 99.0, 535.0, 698.0]
	 33 	 [127.0, 106.0, 535.0, 698.0]
	 34 	 [127.0, 556.0, 534.0, 698.0]

New full page sizes after cropping, in PDF format (lbrt):
	1	 [16.2, 90.9, 541.8, 738]
	2	 [117.9, 89.1, 542.7, 707.4]
	3	 [117.9, 120.6, 542.7, 707.4]
	4	 [117.9, 88.2, 542.7, 707.4]
	5	 [117.9, 96.3, 541.8, 707.4]
	6	 [117.9, 103.5, 541.8, 707.4]
	7	 [117.9, 92.7, 541.8, 707.4]
	8	 [117.9, 88.2, 541.8, 707.4]
	9	 [117.9, 195.3, 548.1, 707.4]
	10	 [117.9, 92.7, 542.7, 707.4]
	11	 [117.9, 89.1, 541.8, 707.4]
	12	 [117.9, 90.9, 542.7, 707.4]
	13	 [137.7, 67.5, 540.9, 707.4]
	14	 [117.9, 99, 542.7, 707.4]
	15	 [117.9, 90.9, 542.7, 707.4]
	16	 [117.9, 90.9, 541.8, 707.4]
	17	 [117, 89.1, 541.8, 707.4]
	18	 [117.9, 54.9, 523.8, 707.4]
	19	 [129.6, 99.9, 541.8, 707.4]
	20	 [117, 90.9, 542.7, 707.4]
	21	 [117.9, 89.1, 541.8, 707.4]
	22	 [117.9, 89.1, 542.7, 707.4]
	23	 [117.9, 90.9, 542.7, 707.4]
	24	 [117.9, 89.1, 542.7, 707.4]
	25	 [117.9, 93.6, 542.7, 707.4]
	26	 [117.9, 89.1, 542.7, 707.4]
	27	 [117.9, 89.1, 542.7, 707.4]
	28	 [117.9, 89.1, 541.8, 707.4]
	29	 [117.9, 89.1, 542.7, 707.4]
	30	 [117.9, 89.1, 542.7, 707.4]
	31	 [117.9, 89.1, 542.7, 707.4]
	32	 [115.2, 89.1, 542.7, 707.4]
	33	 [114.3, 95.4, 542.7, 707.4]
	34	 [114.3, 500.4, 541.8, 707.4]

"""

def convert_box_pymupdf_to_pdf(box_pymupdf, page):
    """Convert a box from PyMuPDF format to PDF format."""
    return fitz.Rect(box_pymupdf)

    # Below was not needed.
    # See: https://github.com/pymupdf/PyMuPDF/issues/317
    transformation_matrix = page.transformation_matrix
    #print("transformation_matrix", transformation_matrix)
    box_pdf = fitz.Rect(box_pymupdf) * ~page.transformation_matrix # Note ~ takes inverse.
    #box_pdf[1], box_pdf[3] = box_pdf[3], box_pdf[1]
    return box_pdf

def convert_box_pdf_to_pymupdf(box_pdf, page):
    """Convert a box from PDF format to PyMuPDF format."""
    return fitz.Rect(box_pdf)

    # Below was not needed.
    # See: https://github.com/pymupdf/PyMuPDF/issues/317
    transformation_matrix = page.transformation_matrix
    #print("transformation_matrix", transformation_matrix)
    box_pymupdf = fitz.Rect(box_pdf) * page.transformation_matrix
    #box_pdf[1], box_pdf[3] = box_pdf[3], box_pdf[1]
    return box_pymupdf

def test_conversions():
    """Test the conversion from pymupdf format to pypdf2 format and back."""
    class page:
        transformation_matrix = fitz.Matrix(1.0, 0.0, 0.0, -1.0, -9.0, 761.0)

    test_box = fitz.Rect(0.0, 0.0, 1006.0, 750.0)

    test_box_pdf = convert_box_pymupdf_to_pdf(test_box, page)

    print("test_box:", test_box)
    print("test_box_pdf:", test_box_pdf)
    assert test_box_pdf == Rect(9.0, 11.0, 1015.0, 761.0)

    test_box_pdf_from_matrix = test_box * ~page.transformation_matrix
    print("test_box_pdf_from_matrix:", test_box_pdf_from_matrix)
    assert test_box_pdf == test_box_pdf_from_matrix

    test_box_recovered = convert_box_pdf_to_pymupdf(test_box_pdf, page)
    print("test_box_recovered:", test_box_recovered)

    assert test_box_recovered == test_box

#test_conversions()

def get_box(page, boxstring):
    """Return the box for the specified box string, converted to PyPDF2 coordinates which
    assume that bottom-left is the origin.  Pymupdf uses the top-left (as does PDF itself).
    It also shifts all but the mediabox to have zero be the reference for the top y value
    (shifting it by the value of the mediabox top y value)."""
    box = getattr(page, boxstring)
    # TODO: Still need to shift for zeroing out of all but mediabox top coord? (see pymupdf glossary)
    # https://pymupdf.readthedocs.io/en/latest/glossary.html#MediaBox
    converted_box = convert_box_pymupdf_to_pdf(box, page)
    #converted_box[1], converted_box[3] = converted_box[3], converted_box[1] # fixes top/bottom prob but crops now negative of original...
    return converted_box

def set_box(page, boxstring, box):
    """Set the box for the specified box string, converted to PyPDF2 coordinates which
    assume that bottom-left is the origin.  See `get_box`."""
    set_box_method = getattr(page, "set_" + boxstring)
    converted_box = convert_box_pdf_to_pymupdf(box, page)
    #converted_box[1], converted_box[3] = converted_box[3], converted_box[1] # fixes top/bottom prob but crops now negative of original...
    set_box_method(converted_box)

class MuPdfDocument:
    """Holds `pyMuPDF` document and PyMuPDF pages of the document for the GUI
    to display.  Has methods to get rendered images.  Note that the page numbering
    convention is from zero."""

    def __init__(self, args):
        """Initialize an empty object.  The `args` parameter should be passed a
        parsed command-line argument object from argparse with the user-selected
        command-line options."""
        self.args = args
        self.clear_cache()
        self.document = None

    def clear_cache(self):
        """Clear the cache of rendered document pages."""
        self.num_pages = 0
        self.page_display_list_cache = []
        self.page_crop_display_list_cache = []

    def open_document(self, doc_fname):
        """Open the document with fitz (PyMuPDF) and return the number of pages."""
        # TODO: How to open a file and repair it:
        # https://pymupdf.readthedocs.io/en/latest/recipes-general.html#how-to-dynamically-clean-up-corrupt-pdfs
        try:
            self.document = fitz.open(doc_fname)
        except RuntimeError:
            print("\nError in pdfCropMargins: The PyMuPDF program could not read"
                  " the document\n   '{}'\nin order to display it in the GUI.   If you"
                  " have Ghostscript installed\nconsider running pdfCropMargins with the"
                  " '--gsFix' option to attempt to repair it."
                  .format(doc_fname), file=sys.stderr)
            ex.cleanup_and_exit(1)

        # Decrypt if necessary.
        if self.document.is_encrypted:
            if self.args.password:
                # Return code is positive for success, negative for failure. If positive,
                #   bit 0 set = no password required
                #   bit 1 set = user password authenticated
                #   bit 2 set = owner password authenticated
                authenticate_code = self.document.authenticate(self.args.password)
                if self.document.is_encrypted:
                    print("\nError in pdfCropMargins: The document was not correctly "
                          "decrypted by PyMuPDF using the password passed in.",
                          file=sys.stderr)
                    ex.cleanup_and_exit(1)
            else: # Try an empty password.
                authenticate_code = self.document.authenticate("")
                if self.document.is_encrypted:
                    print("\nError in pdfCropMargins: The document is encrypted "
                          "and the empty password does not work.  Try passing in a "
                          "password with the '--password' option.",
                          file=sys.stderr)
                    ex.cleanup_and_exit(1)

        # The pages are all kept on a list here to retain their attributes, which are lost
        # when the page.load_page method is called again in pymupdf.
        self.page_list = [page for page in self.document]
        self.num_pages = len(self.document)

        self.page_display_list_cache = [None] * self.num_pages
        self.page_crop_display_list_cache = [None] * self.num_pages
        return self.num_pages

    def get_page_sizes(self):
        """Return a list of the page sizes."""
        size_list = []
        for page in self.document:
            size_list.append((page.rect.width, page.rect.height))
        return size_list

    def page_count(self):
        """Return the number of pages."""
        return self.document.page_count

    def get_max_and_min_page_sizes(self):
        """Return tuples (max_wid, max_ht) and (min_wid, min_ht)."""
        page_sizes = self.get_page_sizes()
        max_page_sizes = (max(p[0] for p in page_sizes), max(p[1] for p in page_sizes))
        min_page_sizes = (min(p[0] for p in page_sizes), min(p[1] for p in page_sizes))
        return max_page_sizes, min_page_sizes

    def get_max_and_min_aspect_ratios(self):
        """Return the maximum and minimum aspect ratios over all the pages."""
        page_sizes = self.get_page_sizes()
        max_ratio = max(p[0]/p[1] for p in page_sizes)
        min_ratio = min(p[0]/p[1] for p in page_sizes)
        return max_ratio, min_ratio

    def get_max_width_and_height(self):
        """Return the maximum width and height (in points) of PDF pages in the
        document."""
        max_wid = -1
        max_ht = -1
        for page in self.document:
            if page.rect.width > max_wid:
                max_wid = page.rect.width
            if page.rect.height > max_ht:
                max_ht = page.rect.height
        return max_wid, max_ht

    def get_metadata(self):
        """Return the metadata from the document."""
        metadata_info = self.document.metadata
        return metadata_info

    def set_metadata(self, metadata_dict):
        """Set the metadata for the document."""
        self.document.set_metadata(metadata_dict)

    def save_document(self, file_path):
        """Save a document, possibly repairing/cleaning it."""
        # See here:
        #    https://pymupdf.readthedocs.io/en/latest/document.html#Document.save

        # TODO: pymupdf upgrade, add a try/except around this.
        self.document.save(file_path)

    def close_document(self):
        """Close the document and clear its pages."""
        self.page_list = []
        self.document.close()
        self.clear_cache()

    def return_pypdf_pdfreader(self):
        """Return a PyPDF `PdfReader` class instance for the current document.  Does not
        close the document."""
        from PyPDF2 import PdfReader

        doc = self.document

        # Save the PyMuPDF document to a temporary file
        tmp_path = ex.get_temporary_filename()
        doc.save(tmp_path)

        # Read the temporary file using PyPDF2 PdfFileReader
        try:
            input_doc_file_object = open(tmp_path, "rb")
        except OSError:
            print("Error in pdfCropMargins: Could not open output document with "
                  "filename '{}'".format(tmp_path))
            ex.cleanup_and_exit(1)

        try:
            strict_mode = False
            input_doc = PdfReader(input_doc_file_object, strict=strict_mode)
            tmp_input_doc = PdfReader(input_doc_file_object, strict=strict_mode)
        except (KeyboardInterrupt, EOFError):
            raise
        except Exception as e: # PyPDF2 can raise various, catch the rest here.
            print("\nError in pdfCropMargins: The PyPDF2 module failed in an"
                  "\nattempt to read this input file:\n   {}\n"
                  "\nIs the file a PDF file?  If so then it may be corrupted."
                  "\nIf you have Ghostscript installed you can attempt to fix"
                  "\nthe document by using the pdfCropMargins option '--gsFix'"
                  "\n(assuming you are not using that option already).  That option"
                  "\ncan also convert some PostScript files to a readable format."
                  "\n\nThe error message was:\n   {}".format(tmp_path, e),
                  file=sys.stderr)
            ex.cleanup_and_exit(1)

        return input_doc, tmp_input_doc, input_doc_file_object

    def get_page_ppm_for_crop(self, page_num, cache=False):
        """Return an unscaled and unclipped `.ppm` file suitable for cropping the page.
        Not indended for displaying in the GUI."""
        # NOTE: The calculated bounding boxes are already saved in GUI, so
        # there is no need to cache these.  After crops the PDF is written
        # out and re-read, which would clear the cache, anyway.

        # NOTE: The default DPI with the identity matrix is 72 DPI.
        # Ghostscript default is 72 DPI and pdftoppm is 150 DPI (the
        # current pdfCropMargins default).
        # https://github.com/pymupdf/PyMuPDF/issues/181

        # Use grayscale for lower memory requirement; good enough for cropping.
        # See: https://pymupdf.readthedocs.io/en/latest/colorspace.html#colorspace
        colorspace = fitz.csGRAY # or fitz.csRGB, or see above.

        if cache:
            page_crop_display_list = self.page_crop_display_list_cache[page_num]
            if not page_crop_display_list:  # Create if not yet there.
                self.page_crop_display_list_cache[page_num] = self.document[
                                                              page_num].get_displaylist()
                page_crop_display_list = self.page_crop_display_list_cache[page_num]
        else:
            page_crop_display_list = self.document[page_num].get_displaylist()

        # https://github.com/pymupdf/PyMuPDF/issues/322 # Also info on opening in Pillow.
        # TODO: Above page also lists a faster way than getting ppm first.

        # Pillow Image: https://pillow.readthedocs.io/en/stable/reference/Image.html
        # Pillow modes: https://pillow.readthedocs.io/en/stable/handbook/concepts.html#concept-modes
        # PyMuPDF Pixmap: https://pymupdf.readthedocs.io/en/latest/pixmap.html#Pixmap.__init__
        # PyMuPDF get_pixmap: https://pymupdf.readthedocs.io/en/latest/page.html#Page.getPixmap

        mat_0 = fitz.Matrix(1, 1)
        # New in PyMuPDF version 1.16.0, annots kwarg for whether to ignore them.
        pixmap = page_crop_display_list.get_pixmap(matrix=fitz.Identity,
                                                  colorspace=colorspace,
                                                  clip=None, alpha=False)
        if self.args:
            # TODO: Is this working right?  Here, you change matrix in get_pixmap:
            # https://stackoverflow.com/questions/63821179/extract-images-from-pdf-in-high-resolution-with-python
            # Is setting actually changing the matrix?
            resolution = self.args.resX, self.args.resY
        pixmap.set_dpi(*resolution)

        # Maybe pgm below??
        image_ppm = pixmap.tobytes("ppm")  # Make PPM image from pixmap for tkinter.
        return image_ppm

    def get_display_page(self, page_num, max_image_size, zoom=False,
                         reset_cached=False):
        """Return a `tkinter.PhotoImage` or a PNG image for a document page
        number.  The `page_num` argument is a 0-based page number.  The
        `zoom` argument is the top-left of old clip rect, and one of -1, 0,
        +1 for dim. x or y to indicate the arrow key pressed.  The
        `max_image_size` argument is the (width, height) of available image
        area."""
        if not reset_cached:
            page_display_list = self.page_display_list_cache[page_num]
        else:
            page_display_list = None

        if not page_display_list:  # Create if not yet there.
            self.page_display_list_cache[page_num] = self.document[page_num].get_displaylist()
            page_display_list = self.page_display_list_cache[page_num]

        page_rect = page_display_list.rect  # The page rectangle.
        clip = page_rect

        # Make sure that all the images across the document will fit the screen.
        max_wid, max_ht = self.get_max_width_and_height()

        nozoom_scale = min(max_image_size[0]/max_wid,
                           max_image_size[1]/max_ht)
        nozoom_mat = fitz.Matrix(nozoom_scale, nozoom_scale)

        if zoom:
            width2 = page_rect.width / 2
            height2 = page_rect.height / 2

            clip = page_rect * 0.5     # Clip rect size is a quarter page.
            top_left = zoom[0]
            top_left.x += zoom[1] * (width2 / 2)     # adjust top-left ...
            top_left.x = max(0, top_left.x)          # according to ...
            top_left.x = min(width2, top_left.x)     # arrow key ...
            top_left.y += zoom[2] * (height2 / 2)    # provided, but ...
            top_left.y = max(0, top_left.y)          # stay within ...
            top_left.y = min(height2, top_left.y)    # the page rect
            clip = fitz.Rect(top_left, top_left.x + width2, top_left.y + height2)

            # Clip rect is ready, now fill it.
            zoom_mat = nozoom_mat * fitz.Matrix(2, 2)  # The zoom matrix.
            pixmap = page_display_list.get_pixmap(alpha=False, matrix=zoom_mat, clip=clip)

        else:  # Show the total page.
            pixmap = page_display_list.get_pixmap(matrix=nozoom_mat, alpha=False)

        #image_png = pixmap.tobytes()  # get the PNG image
        image_height, image_width = pixmap.height, pixmap.width
        image_ppm = pixmap.tobytes("png")  # Make PPM image from pixmap for tkinter.
        image_tl = clip.tl # Clip position (top left).
        return image_ppm, image_tl, image_height, image_width

