# -*- coding: utf-8 -*-
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

from __future__ import print_function, absolute_import
import sys
import warnings
from . import external_program_calls as ex

has_mupdf = True

try: # Extra dependencies for the GUI version.  Make sure they are installed.
    with warnings.catch_warnings():
        #warnings.filterwarnings("ignore",category=DeprecationWarning)
        import fitz
    if not [int(i) for i in fitz.VersionBind.split(".")] >= [1, 16, 17]:
        has_mupdf = False
        MuPdfDocument = None

except ImportError:
    has_mupdf = False
    MuPdfDocument = None

if has_mupdf:

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

        def clear_cache(self):
            """Clear the cache of rendered document pages."""
            self.num_pages = 0
            self.page_display_list_cache = []
            self.page_crop_display_list_cache = []

        def open_document(self, doc_fname):
            """Open the document with fitz (PyMuPDF) and return the number of pages."""
            try:
                self.document = fitz.open(doc_fname)
            except RuntimeError:
                print("\nError in pdfCropMargins: The PyMuPDF program could not read"
                      " the document\n   '{}'\nin order to display it in the GUI.   If you"
                      " have Ghostscript installed\nconsider running pdfCropMargins with the"
                      " '--gsFix' option to attempt to repair it."
                      .format(doc_fname), file=sys.stderr)
                ex.cleanup_and_exit(1)

            if not hasattr(self.document, "is_encrypted"): # TODO: Temporary workaround, PyMuPDF renaming.
                self.document.is_encrypted = self.document.isEncrypted # Version 1.17 vs. version 1.18.

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

            self.num_pages = len(self.document)
            self.page_display_list_cache = [None] * self.num_pages
            self.page_crop_display_list_cache = [None] * self.num_pages
            return self.num_pages

        def close_document(self):
            """Close the document and clear its pages."""
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
                                                                  page_num].getDisplayList()
                    page_crop_display_list = self.page_crop_display_list_cache[page_num]
            else:
                page_crop_display_list = self.document[page_num].getDisplayList()

            # https://github.com/pymupdf/PyMuPDF/issues/322 # Also info on opening in Pillow.
            # TODO: Above page also lists a faster way than getting ppm first.

            # Pillow Image: https://pillow.readthedocs.io/en/stable/reference/Image.html
            # Pillow modes: https://pillow.readthedocs.io/en/stable/handbook/concepts.html#concept-modes
            # PyMuPDF Pixmap: https://pymupdf.readthedocs.io/en/latest/pixmap.html#Pixmap.__init__
            # PyMuPDF getPixmap: https://pymupdf.readthedocs.io/en/latest/page.html#Page.getPixmap

            mat_0 = fitz.Matrix(1, 1)
            # New in PyMuPDF version 1.16.0, annots kwarg for whether to ignore them.
            pixmap = page_crop_display_list.getPixmap(matrix=fitz.Identity,
                                                      colorspace=colorspace,
                                                      clip=None, alpha=False)
            if self.args:
                # TODO: Is this working right?  Here, you change matrix in getPixmap:
                # https://stackoverflow.com/questions/63821179/extract-images-from-pdf-in-high-resolution-with-python
                # Is setting actually changing the matrix?
                resolution = self.args.resX, self.args.resY
            pixmap.setResolution(*resolution) # New setResolution in PyMuPDF 1.16.17.

            # Maybe pgm below??
            image_ppm = pixmap.getImageData("ppm")  # Make PPM image from pixmap for tkinter.
            return image_ppm

        def get_display_page(self, page_num, max_image_size, zoom=False,
                             fit_screen=True, reset_cached=False):
            """Return a `tkinter.PhotoImage` or a PNG image for a document page number.
                - The `page_num` argument is a 0-based page number.
                - The `zoom` argument is the top-left of old clip rect, and one of -1, 0,
                  +1 for dim. x or y to indicate the arrow key pressed.
                - The `max_image_size` argument is the (width, height) of available image area.
            """
            zoom_x = 1
            zoom_y = 1
            scale = fitz.Matrix(zoom_x, zoom_y)

            page_display_list = self.page_display_list_cache[page_num] if not reset_cached else None
            if not page_display_list:  # Create if not yet there.
                self.page_display_list_cache[page_num] = self.document[page_num].getDisplayList()
                page_display_list = self.page_display_list_cache[page_num]

            page_rect = page_display_list.rect  # The page rectangle.
            clip = page_rect

            # Make sure that the image will fit the screen.
            zoom_0 = 1
            if max_image_size: # TODO: this is currently a required param...
                zoom_0 = min(1, max_image_size[0] / page_rect.width, max_image_size[1] / page_rect.height)
                if zoom_0 == 1:
                    zoom_0 = min(max_image_size[0] / page_rect.width, max_image_size[1] / page_rect.height)
            mat_0 = fitz.Matrix(zoom_0, zoom_0)

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
                mat = mat_0 * fitz.Matrix(2, 2)  # The zoom matrix.
                pixmap = page_display_list.getPixmap(alpha=False, matrix=mat, clip=clip)

            else:  # Show the total page.
                pixmap = page_display_list.getPixmap(matrix=mat_0, alpha=False)

            #image_png = pixmap.getPNGData()  # get the PNG image
            image_height, image_width = pixmap.height, pixmap.width
            image_ppm = pixmap.getImageData("ppm")  # Make PPM image from pixmap for tkinter.
            image_tl = clip.tl # Clip position (top left).
            return image_ppm, image_tl, image_height, image_width

