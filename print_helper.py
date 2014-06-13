#!/usr/bin/python2.6
# vim:set et fileencoding=utf8 sw=4:

# Copyright © 2009,2010,2011 Philipp Kern <pkern@debian.org>
# Copyright © 2011,2012 Fabian Knittel <fabian.knittel@lettink.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import getpass
import gzip
import os
import os.path
import psycopg2
import shutil
import subprocess
import string
import sys
import re

from optparse import OptionParser
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Image, Paragraph, Frame
from socket import gethostname
from tempfile import NamedTemporaryFile
from BeautifulSoup import BeautifulSoup

def init_fonts(path):
    pdfmetrics.registerFont(TTFont('Maiandra', os.path.join(path, 'Maian.ttf')))
    pdfmetrics.registerFont(TTFont('Maiandra Bold', os.path.join(path, 'Maiandb.ttf')))
    pdfmetrics.registerFont(TTFont('Maiandra Italic', os.path.join(path, 'Maiandit.ttf')))
    pdfmetrics.registerFontFamily('Maiandra', normal='Maiandra', bold='Maiandra Bold', italic='Maiandra Italic')

class NewsIter(object):
    """Iterator helper class used by News to ensure proper formatting of
    the news items returned by the database.  Takes the rows object
    as fetched from it and yield paragraphs generator-like for the
    headlines and paragraphs."""

    VALID_TAGS = ['b', 'i', 'u', 'p']

    def __init__(self, stylesheet, rows):
        self.stylesheet = stylesheet
        self.rows = rows

    def __iter__(self):
        for row in self.rows:
            try:
                yield Paragraph(row[0], self.stylesheet['Heading2'])
            except ValueError:
                # Skip this entry.
                continue

            style = self.stylesheet['BodyText']

            soup = BeautifulSoup(row[1])

            for tag in soup.findAll(True):
                if tag.name not in NewsIter.VALID_TAGS:
                    tag.hidden = True

            for p in soup.findAll('p') or [soup]:
                 yield Paragraph(p.renderContents(), style)

class News(object):
    """Singleton object that fetches News entries out of the database.
    Connection failures will result in an empty list of items.  The items
    itself are formatted as Platypus Paragraph objects, retrieveable
    through the items method."""

    def __init__(self, stylesheet):
        self.stylesheet = stylesheet
        if not 'conn' in self.__dict__:
            try:
                self._connect()
            except:
                self.conn = None

    def _connect(self):
        self.conn = psycopg2.connect("dbname='fsmi' user='prfproto' host='fsmi-db.fsmi.uni-karlsruhe.de' password='prfproto'")

    # Singleton
    _shared = {}
    def __new__(cls, *args, **kwargs):
        inst = object.__new__(cls)
        inst.__dict__ = cls._shared
        return inst

    def items(self):
        try:
            self._connect()
            cur = self.conn.cursor()
            cur.execute("select headline, content from published_news limit 5")
            return NewsIter(self.stylesheet, cur.fetchall())
        except:
            return iter([])

class CoverPage(object):
    """This CoverPage class is used to construct a two-sided cover page with
    a logo, a description of who and what it's intended to cover and a news
    entry list on its back.  The build method will yield a PDF in the
    target filename specified."""

    def __init__(self, who, what):
        self.who = who
        self.what = what

    @staticmethod
    def _center(text):
        return '<para alignment="center">' + text + '</para>'

    @staticmethod
    def _stylesheet():
        stylesheet = getSampleStyleSheet()
        stylesheet['Heading1'].fontName = 'Maiandra Bold'
        stylesheet['Heading1'].fontSize = 20

        stylesheet['Heading2'].fontName = 'Maiandra Bold'

        stylesheet.add(ParagraphStyle(name='FrontPageName',
                                      parent=stylesheet['Heading1'],
                                      fontSize=60,
                                      spaceBefore=10,
                                      spaceAfter=10,
                                      leading=60))
        return stylesheet

    def build(self, target):
        canvas = Canvas(target, pagesize=A4)
        width, height = A4
        canvas.setPageCompression(0)

        stylesheet = self._stylesheet()

        # News page comes first because the last page will appear on top.
        news_page = [
            Paragraph('<para alignment="center">Termine &amp; Aktuelles</para>', stylesheet['Heading1']),
            Paragraph('<para alignment="center">Immer aktuell unter<br /><font face="courier">http://www.fsmi.uni-karlsruhe.de</font>', stylesheet['Heading2']),
            ]
        news_page.extend(News(stylesheet).items())

        Frame(0, 0, width, height, 30, 30, 30, 30).addFromList(news_page, canvas)
        canvas.showPage()

        # Print owl.
        img = Image(os.path.join(BASE_PATH, 'FS-Eule.png'))
        img.drawHeight = float(img.drawHeight) / img.drawWidth * (width / 2.0)
        img.drawWidth = width / 2.0
        img.hAlign = 'CENTER'
        img.drawOn(canvas, width / 4.0, height / 2.0)

        front_page = [
            Paragraph(self._center('<font face="Maiandra">Ausdruck für</font>'), stylesheet['Heading2']),
            Paragraph(self._center(self.who), stylesheet['FrontPageName']),
            Paragraph(self._center('(' + self.what + ')'), stylesheet['Heading1']),
            ]
        Frame(0, 0, width, height / 2.0 - 50, 20, 6, 20, 6).addFromList(front_page, canvas)
        canvas.showPage()

        canvas.save()

def filter_stream(stream_in, stream_out, replacements, bufsize=1024*1024):
    """Performs regex replacements on a stream forwarded from `stream_in` to
    `stream_out`. The string replacements are provided in the `replacement`
    array, which contains compiled regular expression and replacement string
    pairs.
    The buffer size `bufsize` needs to be at least as large as the length of
    the searched-for string, so that the searched-for string is guaranteed
    to be fully contained within two successive buffer blocks.
    """
    front = stream_in.read(bufsize)
    while len(front) > 0:
        back = stream_in.read(bufsize)
        buf = front + back
        for comp_re, new_str in replacements:
            buf = comp_re.sub(new_str, buf)
        front = buf[:bufsize]
        back = buf[bufsize:]
        stream_out.write(front)
        front = back

def pipe_pdf_to_pcl_5(pdf_in, pcl5_out=subprocess.PIPE):
    return subprocess.Popen(['gs', '-q', '-dNOPAUSE', '-dBATCH',
            '-dPARANOIDSAFER', '-dQUIET', '-sDEVICE=ljet4', '-dIjsUseOutputFD',
            '-sOutputFile=-',
            '-c', '<</.HWMargins[0.27 0 1 6.84 ] /Margins[-2.2 -57]>>setpagedevice', '-'],
            stdin=pdf_in, stdout=pcl5_out)

def pipe_pdf_to_a4_pdf(pdf_in, pdf_out=subprocess.PIPE):
    return subprocess.Popen(['pdfjam', '--a4paper',
            '--quiet', '--outfile', '/dev/stdout', '/dev/stdin'],
            stdin=pdf_in, stdout=pdf_out)

class Sewer(object):
    """A sewer object maintains a list of connected pipes and can wait for all
    pipes to be flushed.  Typically, the pipe objects will be
    :class:`subprocess.Popen` instances.
    """

    def __init__(self):
        self._pipes = []

    def add_pipe(self, name, pipe):
        """Adds a pipe object and an associated, possibly descriptive `name`
        object.  The name is only used during error-reporting.
        """
        self._pipes.append((name, pipe))

    def wait(self):
        """Waits for all pipes to be flushed and returns the names of the pipes
        where the wait failed.  Returns an empty list on success.
        """
        failed_pipes = []
        for name, pipe in self._pipes:
            if pipe.wait() != 0:
                failed_pipes.append(name)
        return failed_pipes

class PrintDocument(object):
    """The PrintDocument class is responsible for piping a single document to a
    specified print spooler stream.

    The document has several attributes like duplex, media type, etc. that will
    be communicated to the printer using PJL and possibly special binary codes.

    The document is expected to be one out of potentially several, so the pipe
    won't be closed.

    The filtered PCL code is expected to be PCL 5e, generated by Ghostscript's
    'ljet4' device.
    """

    PCL_ESC = '\x1b'
    PCL_RESET = PCL_ESC + r'E'

    def __init__(self, stream, usercode, tray, mediatype, staple, duplex=True,
            paper='A4'):
        self.stream = stream
        self.usercode = usercode
        self.tray = tray
        self.mediatype = mediatype
        self.staple = staple
        self.duplex = duplex
        self.paper = paper

    def _write_pjl_escape(self):
        """Writes both the PCL and the PJL printer reset commands and also
        enters PJL mode after the command."""
        self.stream.write(self.PCL_ESC + '%-12345X')

    def _write_pjl_header(self):
        self._write_pjl_escape()

        if self.duplex:
            self.stream.write("@PJL SET DUPLEX=ON\r\n")
            self.stream.write("@PJL SET BINDING=LONGEDGE\r\n")
        else:
            self.stream.write("@PJL SET DUPLEX=OFF\r\n")
        self.stream.write("@PJL SET USERCODE=\"%s\"\r\n" % self.usercode)
        self.stream.write("@PJL SET TRAY=%s\r\n" % self.tray)
        self.stream.write("@PJL SET MEDIATYPE=%s\r\n" % self.mediatype)
        self.stream.write("@PJL SET STAPLE=%s\r\n" % (
                'LEFTTOPVERTPORT' if self.staple else 'OFF'))
        self.stream.write("@PJL SET PAPER=%s\r\n" % self.paper)
        self.stream.write("@PJL SET EDGETOEDGE=YES\r\n")

        self.stream.write("@PJL ENTER LANGUAGE=PCL\r\n")

    def _write_pjl_footer(self):
        self._write_pjl_escape()
        self.stream.write("@PJL RESET\r\n")

    def _write_filtered_pcl5(self, stream_in):
        replacements = []

        # Remove slot selection, as they would override the PJL-settings.
        replacements.append((re.compile(self.PCL_ESC + r'&l' + r'\dH'), ''))

        # Remove page size selection, so that the selections don't interfere
        # with the duplex handling.  In theory it shouldn't cause problems if
        # they're only emitted on even pages, but that's difficult to track
        # here, so remove them all and set the page via PJL.
        replacements.append((re.compile(self.PCL_ESC + r'&l' + r'\d+A'), ''))

        # Remove duplex selection, as they would override the PJL-settings.
        replacements.append((re.compile(self.PCL_ESC + r'&l' + r'\dS'), ''))

        # Remove ljet4's margin settings - they are all wrong.
        replacements.append((re.compile(self.PCL_ESC + r'&l' \
                r'(\+|-)?\d*(\.\d*)?u' \
                r'(\+|-)?\d*(\.\d*)?Z'), ''))

        # Remove number of copies, as they would override the PJL-settings.
        replacements.append((re.compile(self.PCL_ESC + r'&l\d+X'), ''))

        filter_stream(stream_in, self.stream, replacements)

    def stream_pcl5_stream(self, pcl5_stream):
        """Send the PCL5 stream to the printer. Returns True on success.
        """
        self._write_pjl_header()
        self._write_filtered_pcl5(pcl5_stream)
        self._write_pjl_footer()
        return True

    def stream_pcl5_gz_file(self, pcl5_gz_fn):
        """Send the gzipped PCL5 file to the printer. Returns True on success.
        """
        f = gzip.GzipFile(pcl5_gz_fn, 'r')
        try:
            return self.stream_pcl5_stream(f)
        finally:
            f.close()

    def stream_pdf_file(self, pdf_fn, scrub_pdf=True):
        """Send the PDF file to the printer. Returns True on success.
        """
        sewer = Sewer()
        with open(pdf_fn, 'rb') as pdf_in:
            if not scrub_pdf:
                gs_pipe = pipe_pdf_to_pcl_5(pdf_in)
                sewer.add_pipe('ghostscript', gs_pipe)
            else:
                a4_pipe = pipe_pdf_to_a4_pdf(pdf_in)
                sewer.add_pipe('a4 conversion', a4_pipe)
                gs_pipe = pipe_pdf_to_pcl_5(a4_pipe.stdout)
                sewer.add_pipe('ghostscript', gs_pipe)

            self.stream_pcl5_stream(gs_pipe.stdout)

            failed_pipes = sewer.wait()
            if len(failed_pipes) > 0:
                print 'piping for steps %s failed, working on fn: %s' % (
                        str(failed_pipes), pdf_fn)
                return False
            return True

class PrintRegularDocument(PrintDocument):
    def __init__(self, stream, usercode):
        PrintDocument.__init__(self, stream=stream, usercode=usercode,
                tray='TRAY1', mediatype='PLAIN', staple=True)

class PrintCoverDocument(PrintDocument):
    def __init__(self, stream, usercode):
        PrintDocument.__init__(self, stream=stream, usercode=usercode,
                tray='TRAY2', mediatype='USERCOLOR1', staple=False)

class PrintJob(object):
    """The PrintJob class is responsible for submitting a list of documents
    to the print spooler cups.  Some settings like the print job's name
    passed to cups are interface details parsed by the corresponding printer
    driver AffiDeluxeKlausur and should thus not be modified.  This class
    supports printing for both clients and for internal use."""

    def __init__(self, usercode, usercode_cover_page):
        self.usercode = usercode
        self.usercode_cover_page = usercode_cover_page

    def send_job(self, printer, title, cover_page, documents):
        lp_pipe = subprocess.Popen(['lp', '-o', 'raw', '-t', title,
                '-d', printer], stdin=subprocess.PIPE)

        for filename in documents:
            doc = PrintRegularDocument(stream=lp_pipe.stdin,
                    usercode=self.usercode)

            base_fn, ext = os.path.splitext(filename)
            if ext == '.pdf':
                preprocessed_filename = base_fn + '.pcl5.gz'
                if os.path.isfile(preprocessed_filename):
                    print 'Preprocessed file found: %s' % preprocessed_filename
                    if not doc.stream_pcl5_gz_file(preprocessed_filename):
                        print 'pcl5 streaming failed for: %s' % (filename)
                        sys.exit(1)
                else:
                    print 'Converting PDF: %s' % filename
                    if not doc.stream_pdf_file(filename):
                        print 'pdf streaming failed for: %s' % (filename)
                        sys.exit(1)
            else:
                print 'file with unexpected extension (expected PDF): %s' % (
                        filename)
                sys.exit(1)

        if cover_page is not None:
            doc = PrintCoverDocument(stream=lp_pipe.stdin,
                    usercode=self.usercode_cover_page)
            if not doc.stream_pdf_file(cover_page, scrub_pdf=False):
                print 'pdf cover page streaming failed: %s' % (cover_page)
                sys.exit(1)

        lp_pipe.stdin.close()
        if lp_pipe.wait() != 0:
            print 'lp_pipe failed'
            sys.exit(1)

def cache_pdf_file_as_pcl5_gz(pdf_fn, pcl5_gz_fn):
    """Converts the PDF file `pdf_fn` and writes the PCL 5 output to
    `pcl5_gz_fn`.
    """
    sewer = Sewer()
    with open(pdf_fn, 'rb') as pdf_in:
        try:
            pcl5_gz_out = gzip.open(pcl5_gz_fn, 'wb')

            a4_pipe = pipe_pdf_to_a4_pdf(pdf_in)
            sewer.add_pipe('a4 conversion', a4_pipe)

            gs_pipe = pipe_pdf_to_pcl_5(a4_pipe.stdout)
            sewer.add_pipe('ghostscript', gs_pipe)

            # The Popen object expects a real FD, so directly passing gzip's
            # file-like object does not work and we need to explicitly copy the
            # data between the file-like objects.
            shutil.copyfileobj(gs_pipe.stdout, pcl5_gz_out)

            failed_pipes = sewer.wait()
            if len(failed_pipes) > 0:
                print 'piping for steps %s failed, caching fn: %s' % (
                        str(failed_pipes), pdf_fn)
                os.remove(pcl5_gz_fn)
                return False
            return True
        finally:
            pcl5_gz_out.close()

BASE_PATH = os.path.dirname(__file__)

# If this is not an FSMI client, assume that we are on a development machine,
# where the needed fonts should be placed right next to this script.
if gethostname()[0:2] == 'fs':
    FONT_PATH = '/usr/share/fonts/truetype/fsmi-fonts'
else:
    FONT_PATH = BASE_PATH
init_fonts(FONT_PATH)

PRINTER_NAME = 'InfoDrucker'

def print_external(who, what, documents, debug=False):
    with NamedTemporaryFile(suffix='.pdf', delete=(not debug)) as cover:
        CoverPage(who, what).build(cover.name)
        if not debug:
            job = PrintJob(usercode='2222', usercode_cover_page='2223')
            job.send_job(printer=PRINTER_NAME,
                    title=u'Odie-Druck für %s (%s)' % (who, what),
                    cover_page=cover.name,
                    documents=documents)
        else:
            print cover.name

def main(args):
    usage = """\
usage: %prog external "Name for cover" "Description for cover" file1 [fileN ...]
       %prog internal acctno "Name for cover" "Description for cover" file1 [fileN ...]
       %prog cache-only file1 [fileN ...]"""
    parser = OptionParser(usage=usage)
    parser.add_option('-d', '--debug', help='Enable debugging.',
                      action='store_true', dest='debug', default=False)
    (options, args) = parser.parse_args(args)

    if len(args) < 1:
        parser.error('Not enough parameters')

    args.reverse()
    selector = args.pop()
    if selector == 'external':
        if len(args) < 3:
            parser.error('Not enough parameters')

        print_external(unicode(args.pop(), 'utf-8'), unicode(args.pop(), 'utf-8'), args, debug=options.debug)
    elif selector == 'internal':
        if len(args) < 4:
            parser.error('Not enough parameters')

        uid = args.pop()
        who = unicode(args.pop(), 'utf-8')
        what = unicode(args.pop(), 'utf-8')

        with NamedTemporaryFile(suffix='.pdf', delete=(not options.debug)) as cover:
            CoverPage(who, what).build(cover.name)
            if not options.debug:
                job = PrintJob(usercode=uid, usercode_cover_page=uid)
                job.send_job(printer=PRINTER_NAME,
                        title=u'FS-Deluxe-Druck für %s (%s)' % (who, what),
                        cover_page=None,
                        documents=args + [cover.name])
            else:
                print cover.name
    elif selector == 'cache-only':
        if len(args) < 1:
            parser.error('Not enough parameters')

        for fn in args:
            if not os.path.exists(fn):
                print >>sys.stderr, "file not found: %s" % (fn)
                sys.exit(1)
            pcl5_gz_fn = os.path.splitext(fn)[0] + '.pcl5.gz'
            print "caching %s to %s" % (fn, pcl5_gz_fn)
            tmp_pcl5_gz_fn = '%s.tmp' % pcl5_gz_fn
            cache_pdf_file_as_pcl5_gz(fn, tmp_pcl5_gz_fn)
            os.rename(tmp_pcl5_gz_fn, pcl5_gz_fn)
    else:
        print >>sys.stderr, "Invalid selector: %s" % selector
        sys.exit(1)

if __name__ == '__main__':
    main(sys.argv[1:])
