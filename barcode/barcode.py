#! /usr/bin/env python3

# dependencies for generating barcodes:
# ps2pdf
# pdftk
# pdfjam

import config
import os
import subprocess
import socket
import tempfile

from api_utils import document_path
from db.documents import Document
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
YPOS = 680
LEGACY_GS1_CS_ORAL_NAMESPACE = "22140"
LEGACY_GS1_CS_WRITTEN_NAMESPACE = "22150"
LEGACY_GS1_MATH_WRITTEN_NAMESPACE = "22160"
GS1_NAMESPACE = "22141"

def _tmp_path(document, suffix=''):
    dir = os.path.join(tempfile.gettempdir(), 'odie')
    if not os.path.isdir(dir):
        os.makedirs(dir)
    return os.path.join(dir, str(document.id) + suffix)

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
    if document.legacy_id or not document.has_file:
        return
    doc_path = document_path(document.id)
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

class ProtocolError(Exception):
    pass

def is_valid(barcode):
    # see https://en.wikipedia.org/wiki/International_Article_Number_(EAN)#Calculation_of_checksum_digit
    return not sum(int(barcode[i]) * (3 if i % 2 else 1) for i in range(13)) % 10

def document_from_barcode(barcode):
    if not is_valid(barcode):
        return None
    # we assume all our namespaces are the same length
    id = int(barcode[len(GS1_NAMESPACE):-1])
    namespace = barcode[:len(GS1_NAMESPACE)]
    if namespace == LEGACY_GS1_CS_ORAL_NAMESPACE:
        return Document.query.filter_by(document_type='oral', legacy_id=id).first()
    if namespace == LEGACY_GS1_CS_WRITTEN_NAMESPACE:
        return Document.query.filter_by(document_type='written', legacy_id=id, subject='computer science').first()
    if namespace == LEGACY_GS1_CS_WRITTEN_NAMESPACE:
        return Document.query.filter_by(document_type='written', legacy_id=id, subject='mathematics').first()
    if namespace == GS1_NAMESPACE:
        return Document.query.get(id)
    else:
        return None

class BarcodeScanner(object):
    """This implementation of the barcodescannerd protocol ignores
    much of the state machine of the server for ease of implementation.
    Luckily the server's pretty resilient against hijinks.
    """
    def __init__(self, host, port, username):
        username = ('Odie>' + username.replace(' ', '_')).encode('utf-8')
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5)
        self.sock.connect((host, port))
        self._rest = [b'']  # always contains leftover lines from last read
        buf = self.get_line()
        if not buf.startswith('CONNECT 1 '):
            raise ProtocolError("That's... not a barcode scanner you got there")
        # we're connected... relax
        self.sock.settimeout(600)
        self.name = buf[len('CONNECT 1 '):]
        self.sock.sendall(b'CONNECT 1 ' + username + b'\n')
        self.expect('OK')
        self.is_grabbed = False

    def grab(self):
        self.sock.sendall(b'GRAB\n')
        self.expect('OK')
        self.is_grabbed = True

    def __iter__(self):
        """yields a stream of documents"""
        if not self.is_grabbed:
            self.grab()
        try:
            while self.is_grabbed:
                barcode = self.expect('BARCODE ')
                doc = document_from_barcode(barcode)
                if doc:  # ignore unmapped barcodes
                    yield doc
        except (ProtocolError, socket.timeout):
            # Scanner was probably revoked
            self.release()
            return

    def release(self):
        self.sock.sendall(b'RELEASE\n')
        self.is_grabbed = False

    def expect(self, line_prefix):
        response = self.get_line()
        if not response.startswith(line_prefix):
            raise ProtocolError("ERROR: expected %s, got %s" % (line_prefix, response))
        return response[len(line_prefix):]

    def __del__(self):
        try:
            self.sock.sendall(b'\nRELEASE\nQUIT\n')
            self.sock.close()
        except (socket.error, socket.timeout):
            pass

    def get_line(self):
        # how often have I implemented this already?
        if len(self._rest) > 1:
            # we read more than one line on the last read
            r = self._rest[0].decode('utf-8')
            self._rest = self._rest[1:]
            return r
        fragments = self._rest[:]
        while b'\n' not in fragments[-1]:
            fragments.append(self.sock.recv(1024))
        split = fragments[-1].split(b'\n')
        # split is guaranteed to be at least length 2
        fragments[-1] = split[0]
        self._rest = split[1:]
        return b''.join(fragments).decode('utf-8')

# Fetch all scanner names
def scanner_name(host, port):
    try:
        return BarcodeScanner(host, port, 'Odie(tmp)').name
    except (ProtocolError, socket.timeout, socket.error):
        return 'Scanner @ {}:{}'.format(host, port)

for office in config.FS_CONFIG['OFFICES']:
    config.FS_CONFIG['OFFICES'][office]['scanners'] = [scanner_name(h, p) for (h, p) in config.LASER_SCANNERS[office]]
