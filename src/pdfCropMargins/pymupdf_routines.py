"""

This module contains a wrapper class, `MuPdfDocument`, which provides
a wrapper for the PyMuPDF library functions.  The program was originally
written to use the PyPDF library.  Those libraries use some different
conventions, such as the origin of coordinates and shifting of box
values other than the MediaBox.  The wrapper converts between the
formats to return the PyPDF format that the main code expects.

Note that the PyMuPDF program resets all the other boxes when the
`set_mediabox` method is called.  All other boxes must be fully contained
within the mediabox for consistency:
    https://pymupdf.readthedocs.io/en/latest/page.html#Page.set_mediabox

See the `get_box` and `set_box` function comments for other PyMuPDF behavior
that needs to be taken into account (all but mediabox are translated to start
at zero, for example).

=========================================================================

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

Some of this code is heavily modified from the GPL example/demo code found here:
https://github.com/PySimpleGUI/PySimpleGUI/blob/master/DemoPrograms/Demo_PDF_Viewer.py

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
    # Need at least 1.19.4 for setting MediaBox resetting all other boxes behavior.
    # Version 1.19.6 is the last one supporting Python 3.6.
    if not [int(i) for i in fitz.VersionBind.split(".")] >= [1, 19, 4]:
        has_mupdf = False
        MuPdfDocument = None

except ImportError:
    has_mupdf = False
    MuPdfDocument = None

#
# Utility functions.
#

def intersect_pdf_boxes(box1, box2, page):
    """Return the intersection of PDF-style boxes by converting to
    pymupdf `Rect`, using its intersection function, and then
    converting back."""
    # TODO: page argument no longer required, here or in "conversion" routines, maybe remove.
    box1_pymupdf = convert_box_pdf_to_pymupdf(box1, page)
    box2_pymupdf = convert_box_pdf_to_pymupdf(box2, page)
    intersection = box1_pymupdf.intersect(box2_pymupdf)
    return convert_box_pymupdf_to_pdf(intersection, page)

def convert_box_pymupdf_to_pdf(box_pymupdf, page):
    """Convert a box from PyMuPDF format to PDF format."""
    # Note these funs were not needed; this still makes a copy and might be needed later.
    # This issue with raw PDF values didn't matter: https://github.com/pymupdf/PyMuPDF/issues/317
    return fitz.Rect(box_pymupdf)

def convert_box_pdf_to_pymupdf(box_pdf, page):
    """Convert a box from PDF format to PyMuPDF format."""
    # Note these funs were not needed; this still makes a copy and might be needed later.
    # This issue with raw PDF values didn't matter: https://github.com/pymupdf/PyMuPDF/issues/317
    return fitz.Rect(box_pdf)

def get_box(page, boxstring):
    """Return the box for the specified box string, converted to PyPDF2/PDF coordinates which
    assume that bottom-left is the origin. (Pymupdf uses the top-left as the origin).
    It also shifts all but the mediabox to have zero be the reference for the top y value
    (shifting it by the value of the mediabox top y value)."""
    if boxstring != "mediabox":
        mediabox = page.mediabox
    box = getattr(page, boxstring)
    converted_box = convert_box_pymupdf_to_pdf(box, page)

    # Need to shift for pymupdf zeroing out the top y coordinate of all
    # but the mediabox. See the glossary:
    # https://pymupdf.readthedocs.io/en/latest/glossary.html#MediaBox
    if boxstring != "mediabox":
        converted_box[1] += mediabox[1]
        converted_box[3] += mediabox[1]

    return converted_box

def set_box(page, boxstring, box):
    """Set the box for the specified box string, converted to PyPDF2 coordinates which
    assume that bottom-left is the origin.  (PyMuPDF uses the top-left as the origin.
    See `get_box`."""
    if boxstring != "mediabox":
        mediabox = page.mediabox
    set_box_method = getattr(page, "set_" + boxstring)
    converted_box = convert_box_pdf_to_pymupdf(box, page)

    # Need to shift for pymupdf zeroing out the top y coordinate of all
    # but the mediabox. See the glossary:
    # https://pymupdf.readthedocs.io/en/latest/glossary.html#MediaBox
    if boxstring != "mediabox":
        converted_box[1] -= mediabox[1]
        converted_box[3] -= mediabox[1]

    try:
        set_box_method(converted_box)
    except ValueError:
        print(f"\nWarning in pdfCropMargins: The {boxstring} could not be written"
              f" to the page,\nprobably a conflict with the mediabox.",
              file=sys.stdout)

#
# The main class.
#

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

    def get_box_list(self, boxstring):
        """Get a list of all the boxes of the type `boxstring`, e.g. `"artbox"`
        or `"mediabox"`."""
        boxlist = []
        for page in self.document:
            boxlist.append(get_box(page, boxstring))
        return boxlist

    def save_document(self, file_path):
        """Save a document, possibly repairing/cleaning it."""
        # See here:
        #    https://pymupdf.readthedocs.io/en/latest/document.html#Document.save
        self.document.save(file_path)

    def close_document(self):
        """Close the document and clear its pages."""
        self.page_list = []
        self.document.close()
        self.clear_cache()

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

    def get_standard_metadata(self):
        """Return the standard metadata from the document."""
        metadata_info = self.document.metadata
        return metadata_info

    def set_standard_metadata(self, metadata_dict):
        """Set the standard metadata dict for the document."""
        self.document.set_metadata(metadata_dict)

    def has_xml_metadata_key(self, key):
        """Return a boolean indicating if the XML metadata dict has the key `key`."""
        data_type, value = self.document.xref_get_key(-1, "Info")  # /Info key in the trailer
        if data_type != "xref":
            return None # No metadata at all.
        else:
            xref = int(value.replace("0 R", ""))  # Extract the metadata xref.
            if key in self.document.xref_get_keys(xref):
                return True
            return False

    def get_xml_metadata(self):
        """Return a copy of the XML metadata dict with all the items, not just the
        standard ones."""
        # https://pymupdf.readthedocs.io/en/latest/recipes-low-level-interfaces.html#how-to-extend-pdf-metadata
        metadata = {}  # Make a local metadata dict.

        data_type, value = self.document.xref_get_key(-1, "Info")  # /Info key in the trailer
        if data_type != "xref":
            has_xml_metadata = False # No metadata at all.
        else:
            has_xml_metadata = True
            xref = int(value.replace("0 R", ""))  # Extract the metadata xref.
            for key in self.document.xref_get_keys(xref):
                metadata[key] = self.document.xref_get_key(xref, key)[1]

        return has_xml_metadata, metadata

    def get_xml_metadata_value(self, key):
        """Return the XML metadata with the given key, if available.  Returns `None`
        if there is no metadata or if the key is not present in the dict.  Also
        returns booleans `has_xml_metadata` and `has_key` so failures can be
        diagnosed."""
        # https://pymupdf.readthedocs.io/en/latest/recipes-low-level-interfaces.html#how-to-extend-pdf-metadata
        data_value = None
        has_key = False
        has_xml_metadata, metadata = self.get_xml_metadata()

        if not has_xml_metadata:
            return data_value, has_xml_metadata, has_key # No metadata at all.

        if key in metadata:
            has_key = True
            data_value = metadata[key]
        return data_value, has_xml_metadata, has_key

    def set_xml_metadata_item(self, key, data_string):
        """Set XML metadata with the arbitrary string `data_string` as the data.  Any
        key can be used also, provided it is compliant with PDF specs.  To delete data
        for a key set the key to have the string "null" as its data value."""
        # https://pymupdf.readthedocs.io/en/latest/recipes-low-level-interfaces.html#how-to-extend-pdf-metadata
        data_type, value = self.document.xref_get_key(-1, "Info")  # /Info key in the trailer
        if data_type != "xref":
            raise ValueError("PDF has no metadata, cannot set XML metadata.")

        xref = int(value.replace("0 R", ""))  # Extract the metadata xref.
        pdf_data_string = fitz.get_pdf_str(data_string) # Convert the string format.

        self.document.xref_set_key(xref, key, pdf_data_string) # Add the data info.

    def delete_xml_metadata_item(self, key):
        """Delete the key `key` and the data associated with it."""
        # TODO: This doesn't seem to delete the key like the docs say, only the metadata.
        # https://pymupdf.readthedocs.io/en/latest/recipes-low-level-interfaces.html#how-to-extend-pdf-metadata
        self.set_xml_metadata_item(key, "null")

