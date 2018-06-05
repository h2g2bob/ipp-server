from __future__ import division
from __future__ import absolute_import
from __future__ import print_function

from io import BytesIO
import threading
try:
    import socketserver
except ImportError:
    import SocketServer as socketserver
try:
    from http.server import BaseHTTPRequestHandler
except ImportError:
    from BaseHTTPServer import BaseHTTPRequestHandler
import time
import logging
import os.path

from . import request


def local_file_location(filename):
    return os.path.join(os.path.dirname(__file__), 'data', filename)


def _get_next_chunk(rfile):
    while True:
        chunk_size_s = rfile.readline()
        logging.debug('chunksz=%r', chunk_size_s)
        if not chunk_size_s:
            raise RuntimeError(
                'Socket closed in the middle of a chunked request'
            )
        if chunk_size_s.strip() != b'':
            break

    chunk_size = int(chunk_size_s, 16)
    if chunk_size == 0:
        return b''
    chunk = rfile.read(chunk_size)
    logging.debug('chunk=0x%x', len(chunk))
    return chunk


def read_chunked(rfile):
    chunks = []
    while True:
        chunk = _get_next_chunk(rfile)
        if chunk == b'':
            break
        chunks.append(chunk)

    return b''.join(chunks)


class IPPRequestHandler(BaseHTTPRequestHandler):
    default_request_version = "HTTP/1.1"
    protocol_version = "HTTP/1.1"

    def parse_request(self):
        ret = BaseHTTPRequestHandler.parse_request(self)
        if 'chunked' in self.headers.get('transfer-encoding', ''):
            r = read_chunked(self.rfile)
            self.rfile.close()
            self.rfile = BytesIO(r)
        self.close_connection = True
        return ret

    if not hasattr(BaseHTTPRequestHandler, "send_response_only"):
        def send_response_only(self, code, message=None):
            """Send the response header only."""
            if message is None:
                if code in self.responses:
                    message = self.responses[code][0]
                else:
                    message = ''
            if not hasattr(self, '_headers_buffer'):
                self._headers_buffer = []
            self._headers_buffer.append(
                (
                    "%s %d %s\r\n" % (self.protocol_version, code, message)
                ).encode('latin-1', 'strict')
            )

    def log_error(self, format, *args):
        logging.error(format, *args)

    def log_message(self, format, *args):
        logging.debug(format, *args)

    def send_headers(self, status=200, content_type='text/plain',
                     content_length=None):
        self.log_request(status)
        self.send_response_only(status, None)
        self.send_header('Server', 'ipp-server')
        self.send_header('Date', self.date_time_string())
        self.send_header('Content-Type', content_type)
        if content_length:
            self.send_header('Content-Length', '%u' % content_length)
        self.send_header('Connection', 'close')
        self.end_headers()

    def do_POST(self):
        self.handle_ipp()

    def do_GET(self):
        self.handle_www()

    def handle_www(self):
        if self.path == '/':
            self.send_headers(
                status=200, content_type='text/plain'
            )
            with open(local_file_location('homepage.txt'), 'rb') as wwwfile:
                self.wfile.write(wwwfile.read())
        elif self.path.endswith('.ppd'):
            self.send_headers(
                status=200, content_type='text/plain'
            )
            self.wfile.write(self.server.behaviour.ppd.text())
        else:
            self.send_headers(
                status=404, content_type='text/plain'
            )
            with open(local_file_location('404.txt'), 'rb') as wwwfile:
                self.wfile.write(wwwfile.read())

    def handle_expect_100(self):
        """ Disable """
        return True

    def handle_ipp(self):
        self.ipp_request = request.IppRequest.from_file(self.rfile)

        if self.server.behaviour.expect_page_data_follows(self.ipp_request):
            self.send_headers(
                status=100, content_type='application/ipp'
            )
            postscript_file = self.rfile.read()
        else:
            postscript_file = None

        ipp_response = self.server.behaviour.handle_ipp(
            self.ipp_request, postscript_file
        ).to_string()
        self.send_headers(
            status=200, content_type='application/ipp',
            content_length=len(ipp_response)
        )
        self.wfile.write(ipp_response)


class IPPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, address, request_handler, behaviour):
        self.behaviour = behaviour
        socketserver.ThreadingTCPServer.__init__(self, address, request_handler)  # old style class!


def wait_until_ctrl_c():
    try:
        while True:
            time.sleep(300)
    except KeyboardInterrupt:
        return


def run_server(server):
    logging.info('Listening on %r', server.server_address)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    wait_until_ctrl_c()
    logging.info('Ready to shut down')
    server.shutdown()
