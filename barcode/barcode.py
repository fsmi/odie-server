#! /usr/bin/env python3

# dependencies for this script:
# ps2pdf
# pdftk
# pdfjam

import config
import os
import subprocess

from api_utils import document_path
from subprocess import PIPE, DEVNULL

BARCODE_PS_FILE = os.path.join(os.path.dirname(__file__), 'barcode.ps')
BARCODE_TEMPLATE = """%
{xpos} {ypos} moveto ({barcode}) (includetext) ean13 barcode
showpage
"""

# The coordinates here follow the usual convention, not the ps one:
# origin is in the bottom left, x points right, y points up.
# the default X and y positions were extracted from fs-deluxe.

XPOS = 350
YPOS = 670
LEGACY_GS1_NAMESPACE = "22140"
GS1_NAMESPACE = "22141"

def _tmp_path(document, suffix=''):
    dir = os.path.join(config.DOCUMENT_DIRECTORY, 'tmp')
    if not os.path.isdir(dir):
        os.makedirs(dir)
    return os.path.join(dir, document.file_id + suffix)

def bake_barcode(document):
    """Put a generated barcode onto the PDF

    The pipeline works as follows:
    barcode.ps is piped into ps2pdf, followed by the call to the barcode-generating
    function. The resulting one-page PDF containing only the barcode is read into
    memory.
    This is then piped into pdftk, which grafts the barcode onto the first page
    of the document (discarding all other pages).
    We dump all but the first page of the document and concatenate our modified
    first page to it (via pdfjam).
    If this sounds somewhat roundabout, that's because it is.
    """

    # if the document has a legacy_id, the PDF already has a barcode.
    if document.legacy_id or not document.file_id:
        return
    doc_path = document_path(document.file_id)
    # The barcodes we use have 13 digits. The last one is a checksum digit. barcode.ps takes care of this.
    barcode = GS1_NAMESPACE + str(document.id).zfill(12 - len(GS1_NAMESPACE))
    with open(BARCODE_PS_FILE, 'rb') as barcode_file:
        ps2pdf = subprocess.Popen(['ps2pdf', '-', '-'], stdin=PIPE, stdout=PIPE)
        (barcode_pdf, _) = ps2pdf.communicate(barcode_file.read() +
                BARCODE_TEMPLATE.format(xpos=XPOS, ypos=YPOS, barcode=barcode).encode('utf-8'))
    assert ps2pdf.returncode == 0

    # pdftk outputs a pdf with only one page, discarding the rest of the PDF
    pdftk = subprocess.Popen(
            ['pdftk', '-', 'background', doc_path, 'output', '-'],
            stdin=PIPE,
            stdout=PIPE
    )
    (pdf_with_barcode, _) = pdftk.communicate(barcode_pdf)
    with open('out', 'wb') as outf:
        outf.write(pdf_with_barcode)
    if document.number_of_pages > 1:
        rest_path = _tmp_path(document, '-rest.pdf')
        subprocess.check_call(
                ['pdfjam', '--nup', '1x1', doc_path, '2-', '--outfile', rest_path],
                stderr=DEVNULL)
        pdfjam = subprocess.Popen(
                ['pdfjam', '--fitpaper', 'true', '/dev/stdin', rest_path, '--outfile', doc_path],
                stdin=PIPE,
                stderr=DEVNULL)
        pdfjam.communicate(pdf_with_barcode)
        os.unlink(rest_path)
    else:
        with open(doc_path, 'wb') as document_file:
            document_file.write(pdf_with_barcode)
