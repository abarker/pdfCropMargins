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
from . import external_program_calls as ex

has_mupdf = True

try: # Extra dependencies for the GUI version.  Make sure they are installed.
    with warnings.catch_warnings():
        #warnings.filterwarnings("ignore",category=DeprecationWarning)
        import fitz
    # Need at least 1.19.4 for setting MediaBox resetting all other boxes behavior.
    # Version 1.19.6 is the last one supporting Python 3.6.
    if not [int(i) for i in fitz.VersionBind.split(".")] >= [1, 19, 4]:
        has_mupdf = False
        MuPdfDocument = None

except ImportError:
    has_mupdf = False
    MuPdfDocument = None

# The string which is appended to Producer metadata in cropped PDFs.
PRODUCER_MODIFIER = " (Cropped by pdfCropMargins.)" # String for older versions.
PRODUCER_MODIFIER_2 = " (Cropped by pdfCropMargins>=2.0.)" # Added to Producer metadata.
RESTORE_METADATA_KEY = "pdfCropMarginsRestoreData" # Key for XML dict restore data.

# Limit precision to some reasonable amount to prevent problems in some PDF viewers.
DECIMAL_PRECISION_FOR_MARGIN_POINT_VALUES = 8

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

    # Normalizing replaces the rectangle with its valid version.
    # https://pymupdf.readthedocs.io/en/latest/rect.html#Rect.normalize
    box = fitz.Rect(box_pdf).normalize()
    return box

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
    #    https://pymupdf.readthedocs.io/en/latest/glossary.html#MediaBox
    #
    # Maybe consider using mediabox.y1 to access?  Maybe round values or take
    # max/min with the original values to deal with inexact issues?  Force it
    # to be inside mediabox to avoid "rect not in mediabox" error?
    #    https://github.com/pymupdf/PyMuPDF/issues/1616
    if boxstring != "mediabox":
        converted_box[1] += mediabox[1]
        converted_box[3] += mediabox[1]

    return converted_box

def set_box(page, boxstring, box, intersect_with_mediabox=False):
    """Set the box for the specified box string, converted to PyPDF2 coordinates which
    assume that bottom-left is the origin.  (PyMuPDF uses the top-left as the origin.
    See `get_box`."""
    #print(f"\n\n====================\nSetting box {boxstring} to value {box}") # DEBUG
    #print_page_boxes(page) # DEBUG
    set_box_method = getattr(page, "set_" + boxstring)
    converted_box = convert_box_pdf_to_pymupdf(box, page)
    #print(f"\nconverted box is {converted_box}") # DEBUG

    if intersect_with_mediabox: # TODO: If true negative absolute crops after first crop do nothing...
        converted_box = intersect_pdf_boxes(page.mediabox, converted_box, page)

    # Need to shift for pymupdf zeroing out the top y coordinate of all
    # but the mediabox. See the glossary:
    #    https://pymupdf.readthedocs.io/en/latest/glossary.html#MediaBox
    #       "MediaBox is the only rectangle, for which there is no difference
    #       between MuPDF and PDF coordinate systems: Page.mediabox will always
    #       show the same coordinates as the /MediaBox key in a page’s object
    #       definition. For all other rectangles, MuPDF transforms y coordinates
    #       such that the top border is the point of reference.
    if boxstring != "mediabox":
        converted_box[1] -= page.mediabox[1]
        converted_box[3] -= page.mediabox[1]

    try:
        set_box_method(converted_box)
        #print_page_boxes(page) # DEBUG
    except ValueError as e:
        print(f"\nWarning in pdfCropMargins: The {boxstring} could not be written"
              f" to page {page.number}.  The error is:\n   {str(e)}",
              file=sys.stdout)

def mod_box_for_rotation(box, angle, undo=False):
    """The user sees left, bottom, right, and top margins on a page, but inside
    the PDF and in pyPdf the page may be rotated (such as in landscape mode).
    In the case of 90 degree clockwise rotation the left really modifies the
    top, the top really modifies right, and so forth.  In order for the options
    like '--percentRetain4' and '--absoluteOffset4' to work as expected the
    values need to be shifted to match any "hidden" rotations on any page.
    The `box` argument is a 4-tuple of left, bottom, right, top values."""
    def rotate_ninety_degrees_clockwise(box, n):
        """The `n` here is the number of 90deg rotations to do."""
        if n == 0:
            return box
        box = rotate_ninety_degrees_clockwise(box, n-1)
        return [box[1], box[2], box[3], box[0]]

    # These are for clockwise, swap do and undo to reverse.
    do_map = {0: 0, 90: 1, 180: 2, 270: 3} # Map angle to num of 90deg rotations.
    undo_map = {0: 0, 90: 3, 180: 2, 270: 1}

    if not undo:
        return rotate_ninety_degrees_clockwise(box, do_map[angle])
    else:
        return rotate_ninety_degrees_clockwise(box, undo_map[angle])

def serialize_boxlist(boxlist):
    """Return the string for the list of boxes."""
    return str([list(b) for b in boxlist])

def deserialize_boxlist(boxlist_string):
    """Return the string for the list of boxes."""
    if boxlist_string[0] != "[" or boxlist_string[-1] != "]":
        return None
    boxlist_string = boxlist_string[2:-2]
    split_list = boxlist_string.split("], [")
    deserialized_boxlist = []
    for box in split_list:
        values = box.split(",")
        try:
            deserialized_boxlist.append([float(v) for v in values])
        except ValueError:
            return None
    return deserialized_boxlist

def print_page_boxes(page):
    """Debugging routine."""
    mediabox = page.rect
    print(f" MediaBox: {mediabox}")
    cropbox = page.cropbox
    print(f" CropBox: {cropbox}")
    if page.bleedbox:
        print(f" BleedBox: {page.bleedbox}")
    if page.trimbox:
        print(f" TrimBox: {page.trimbox}")
    if page.artbox:
        print(f" ArtBox: {page.artbox}")
    print() # Add a newline for readability

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
        # TODO: Consider adding a garbage-collection option, maybe garbage=1 instead
        # of the default 0.
        self.document.save(file_path)

    def close_document(self):
        """Close the document and clear its pages."""
        self.page_list = []
        self.clear_cache()
        self.document.close()

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

        #mat_0 = fitz.Matrix(1, 1)
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

    def get_full_page_box_list_assigning_media_and_crop(self, quiet=False):
        """Get a list of all the full-page box values for each page.  The boxes on
        the list are in the simple 4-float list format.  This is also where any
        pre-crop is applied."""

        def get_full_page_box_assigning_media_and_crop(page):
            """This returns whatever PDF box was selected (by the user option
            '--fullPageBox') to represent the full page size.  All cropping is done
            relative to this box.  The default selection option is the MediaBox
            intersected with the CropBox so multiple crops work as expected.

            The argument page should be a pyPdf page object.

            This function also sets the MediaBox and CropBox of the page to the
            full-page size and saves the old values in the same page namespace, so it
            should only be called once for each page.  It returns a `RectangleObject`
            box."""

            # Find the page rotation angle (degrees).
            # Note rotation is clockwise, and four values are allowed: 0 90 180 270
            rotation = page.rotation
            while rotation >= 360:
                rotation -= 360
            while rotation < 0:
                rotation += 360

            # Save the rotation value in the page's namespace so we can restore it later.
            page.rotationAngle = rotation

            # Un-rotate the page, to a rotation of 0.
            page.set_rotation(0)

            # Save copies of some values in the page's namespace, to possibly restore later.
            page.original_media_box = get_box(page, "mediabox") # TODO: Why was this necessary in the first place?
            #page.original_crop_box = get_box(page, "cropbox") # TODO, see other place where this was used.

            # Note: The default value of empty args.fullPageBox are set when processing the
            # command-line args.  Set to ["m", "c"] unless Ghostscript box-finding is selected.

            first_loop = True
            for box_string in self.args.fullPageBox:
                if box_string == "m":
                    f_box = get_box(page, "mediabox")
                if box_string == "c":
                    f_box = get_box(page, "cropbox")
                if box_string == "t":
                    f_box = get_box(page, "trimbox")
                if box_string == "a":
                    f_box = get_box(page, "artbox")
                if box_string == "b":
                    f_box = get_box(page, "bleedbox")

                # Take intersection over all chosen boxes.
                if first_loop:
                    full_box = f_box
                else:
                    full_box = intersect_pdf_boxes(full_box, f_box, page)

                first_loop = False

            return rotation, full_box, page

        def apply_precrop(rotation, full_box, page):
            """Apply the precrop to the document's box settings."""
            # Do any absolute pre-cropping specified for the page (after modifying any
            # absolutePreCrop4 arguments to take into account rotations to the page).
            precrop_box = mod_box_for_rotation(self.args.absolutePreCrop4, rotation)

            full_box = [float(full_box[0]) + precrop_box[0],
                        float(full_box[1]) + precrop_box[1],
                        float(full_box[2]) - precrop_box[2],
                        float(full_box[3]) - precrop_box[3],
                        ]

            # Note that MediaBox is set FIRST, since PyMuPDF will reset all other boxes
            # when it is set.
            set_box(page, "mediabox", full_box)
            set_box(page, "cropbox", full_box)
            return full_box

        full_page_box_list = []
        rotation_list = []

        if self.args.verbose and not quiet:
            print(f"\nOriginal full page sizes (rounded to "
                  f"{DECIMAL_PRECISION_FOR_MARGIN_POINT_VALUES} digits) in PDF format (lbrt):")

        for page_num in range(self.num_pages):

            # Get the current page and find the full-page box.
            curr_page = self.page_list[page_num]
            rotation, full_box, page = get_full_page_box_assigning_media_and_crop(curr_page)

            # Do any absolute pre-cropping specified for the page (after modifying any
            # absolutePreCrop4 arguments to take into account rotations to the page).
            full_page_box = apply_precrop(rotation, full_box, page)

            if self.args.verbose and not quiet:
                # Want to display page num numbering from 1, so add one.
                rounded_box_string = ", ".join([str(round(f,
                            DECIMAL_PRECISION_FOR_MARGIN_POINT_VALUES)) for f in full_page_box])
                print(f"\t{str(page_num+1)}   rot = "
                      f"{curr_page.rotationAngle}  \t [{rounded_box_string}]")

            ordinary_box = [float(b) for b in full_page_box]
            full_page_box_list.append(ordinary_box)

            # Append the rotation value to the rotation_list.
            rotation_list.append(curr_page.rotationAngle)

        return full_page_box_list, rotation_list

    def get_standard_metadata(self):
        """Return the standard metadata from the document."""
        metadata_info = self.document.metadata
        return metadata_info

    def set_standard_metadata(self, metadata_dict):
        """Set the standard metadata dict for the document."""
        self.document.set_metadata(metadata_dict)

    def check_and_set_crop_metadata(self, metadata_info):
        """First check the producer metadata attribute to see if this program was
        cropped document before.  Returns the variable
        `already_cropped_by_this_program` which is either `False` or has the value
        string `"<2.0"` or `">=2.0".

        The "Producer" metadata then has a string appended (if not already there)
        to indicate that this program modified the file."""
        def has_xml_restore_data():
            """This function is a workaround because setting the XML metadata key
            to "null" doesn't seem to delete the key itself like the docs say.  Need
            to look at the value to determine if there is data there to determine
            `already_cropped_by_this_program` since value is set null on restore."""
            # TODO: Should be able to just check key with `doc_wrap.has_xml_metadata_key`
            # but doesn't work.
            data_value, has_xml_metadata, has_key = self.get_xml_metadata_value(
                                                                RESTORE_METADATA_KEY)
            if has_key:
                return data_value[0] == "["
            return False

        if metadata_info:
            old_producer_string = metadata_info["producer"]
        else:
            return PRODUCER_MODIFIER, False # Can't read metadata, but maybe can set it.

        if has_xml_restore_data(): # See note in function.
            if self.args.verbose:
                print("\nThe document was already cropped at least once by pdfCropMargins>=2.0.")
            already_cropped_by_this_program = ">=2.0"

        elif old_producer_string and old_producer_string.endswith(PRODUCER_MODIFIER):
            if self.args.verbose:
                print("\nThe document was already cropped at least once by pdfCropMargins<2.0.")
            already_cropped_by_this_program = "<2.0"
            # Update the Producer suffix to the the new PRODUCER_MODIFIER_2.
            new_producer_string = old_producer_string.replace(PRODUCER_MODIFIER, PRODUCER_MODIFIER_2)
            metadata_info["producer"] = new_producer_string

        else:
            if self.args.verbose:
                print("\nThe document was not previously cropped by pdfCropMargins.")
            metadata_info["producer"] = metadata_info["producer"] + PRODUCER_MODIFIER_2
            already_cropped_by_this_program = False

        self.set_standard_metadata(metadata_info)
        return already_cropped_by_this_program

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

    def save_old_boxes_for_restore(self, original_mediabox_list,
                                   original_cropbox_list, original_artbox_list,
                                   already_cropped_by_this_program):
        """Save the intersection of the cropbox and the mediabox."""
        if already_cropped_by_this_program == "<2.0":
            old_boxes_to_save_list = original_artbox_list
        else:
            old_boxes_to_save_list = [] # Save list of old boxes to possibly save for later restore.
            for page_num in range(self.document.page_count):
                curr_page = self.page_list[page_num]

                # Do the save for later restore if that option is chosen and Producer is not set.
                box = intersect_pdf_boxes(original_mediabox_list[page_num],
                                          original_cropbox_list[page_num], curr_page)
                old_boxes_to_save_list.append(box)

        serialized_saved_boxes_list = serialize_boxlist(old_boxes_to_save_list)
        self.set_xml_metadata_item(RESTORE_METADATA_KEY,
                                                            serialized_saved_boxes_list)

    def apply_restore_operation(self, already_cropped_by_this_program, original_artbox_list):
        """Restore the saved page boxes to the document."""
        if self.args.writeCropDataToFile:
            self.args.writeCropDataToFile = ex.get_expanded_path(self.args.writeCropDataToFile)
            f = open(self.args.writeCropDataToFile, "w")
        else:
            f = None

        if already_cropped_by_this_program == ">=2.0":
            saved_boxes, has_xml_metadata, xml_metadata_has_key = (
                    self.get_xml_metadata_value(RESTORE_METADATA_KEY))
            saved_boxes_list = deserialize_boxlist(saved_boxes)
            if not saved_boxes_list:
                print("\nError in pdfCropMargins: Could not deserialize the data saved for the"
                        "\nrestore operation.  Deleting the key and the data.", file=sys.stderr)
                self.delete_xml_metadata_item(RESTORE_METADATA_KEY)

        elif already_cropped_by_this_program == "<2.0":
            saved_boxes_list = original_artbox_list

        if not saved_boxes_list or len(saved_boxes_list) != self.num_pages:
            print("\nError in pdfCropMargins: The number of pages in the saved restore"
                  "\ndata is not the same as the number of pages in the document.  The"
                  "\nrestore operation will be ignored.", file=sys.stderr)
            return

        for page_num in range(self.document.page_count):
            curr_page = self.page_list[page_num]

            # Restore any rotation which was originally on the page.
            curr_page.set_rotation(curr_page.rotationAngle)

            # Restore the MediaBox and CropBox to the saved values.  Note that
            # MediaBox is set FIRST, since PyMuPDF will reset all other boxes
            # when it is set.
            # TODO: Should restore respect the --boxesToSet option?
            set_box(curr_page, "mediabox", saved_boxes_list[page_num])
            set_box(curr_page, "cropbox", saved_boxes_list[page_num])
            if self.args.writeCropDataToFile:
                print("\t"+str(page_num+1)+"\t", saved_boxes_list[page_num], file=f)

        # The saved restore data is no longer needed.
        if self.args.verbose:
            print("\nDeleting the saved restore metadata since it is no longer needed.")
        self.delete_xml_metadata_item(RESTORE_METADATA_KEY)

        if self.args.writeCropDataToFile:
            f.close()
            ex.cleanup_and_exit(0)

    def apply_crop_list(self, crop_list, page_nums_to_crop, already_cropped_by_this_program):
        """Apply the crop list to the pages of the input document."""
        args = self.args

        if args.writeCropDataToFile:
            args.writeCropDataToFile = ex.get_expanded_path(args.writeCropDataToFile)
            f = open(args.writeCropDataToFile, "w")
        else:
            f = None

        if args.verbose:
            print("\nNew full page sizes after cropping, in PDF format (lbrt):")

        # Set the appropriate PDF boxes on each page.
        for page_num in range(self.document.page_count):
            curr_page = self.page_list[page_num]

            # Restore any rotation which was originally on the page.
            curr_page.set_rotation(curr_page.rotationAngle)

            # Reset the CropBox and MediaBox to their saved original values (they
            # were saved by `get_full_page_box_assigning_media_and_crop` in the
            # `curr_page` object's namespace).  Restore the MediaBox and CropBox to
            # the saved values.  Note that MediaBox is set FIRST, since PyMuPDF
            # will reset all other boxes when it is set.
            set_box(curr_page, "mediabox", curr_page.original_media_box)
            # TODO: Below causes problems to reset the old one, inconsistent sometimes...,
            # but not really needed since setting MediaBox in PyMuPDF now resets it anyway...
            # Delete where it is set, also, if deleting this code.  Maybe need a copy when set?
            # Note that --boxesToUse was updated to say that only MediaBox is set (to
            # intersection of old MediaBox and CropBox).
            #set_box(curr_page, "cropbox", curr_page.original_crop_box)

            # Copy the original page without further mods if it wasn't in the range
            # selected for cropping.
            if page_num not in page_nums_to_crop:
                continue

            rounded_values = [round(f, DECIMAL_PRECISION_FOR_MARGIN_POINT_VALUES)
                                    for f in crop_list[page_num]]
            new_cropped_box = rounded_values

            if args.verbose:
                print("\t"+str(page_num+1)+"\t", list(new_cropped_box)) # page numbering from 1
            if args.writeCropDataToFile:
                print("\t"+str(page_num+1)+"\t", list(new_cropped_box), file=f)

            if not args.boxesToSet:
                args.boxesToSet = ["m"]

            # Now set any boxes which were selected to be set via the '--boxesToSet' option.
            if "m" in args.boxesToSet:
                # Note the MediaBox is always set FIRST, since it resets the other boxes.
                set_box(curr_page, "mediabox", new_cropped_box)
            if "c" in args.boxesToSet:
                set_box(curr_page, "cropbox", new_cropped_box)
            if "t" in args.boxesToSet:
                set_box(curr_page, "trimbox", new_cropped_box)
            if "a" in args.boxesToSet:
                set_box(curr_page, "artbox", new_cropped_box)
            if "b" in args.boxesToSet:
                set_box(curr_page, "bleedbox", new_cropped_box)

        if args.writeCropDataToFile:
            f.close()
            ex.cleanup_and_exit(0)


