from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from abc import ABCMeta, abstractmethod
import re
import logging


class ConnectionClosedError(Exception):
    pass

_parse_http = re.compile(br'^(GET|POST) (/[^ ]*) HTTP/')

def _process_status(f):
    first_line = f.readline()
    if first_line == b'':
        raise ConnectionClosedError('While reading status line')
    m = _parse_http.search(first_line)
    if m is None:
        raise ValueError('Invalid request: %r' % (first_line,))
    return m.groups()


def _process_headers(f):
    headers = {}
    while True:
        line = f.readline().rstrip(b'\r\n')
        if line == b'':
            break
        try:
            key, value = line.split(b':', 1)
            headers[key.lower().strip()] = value.strip()
        except ValueError:
            logging.warn('Invalid header %r', line)
    logging.debug('headers: %r', headers)
    return headers


class BodyReader(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def read(self, size):
        raise NotImplementedError()


class ContentLengthBodyReader(BodyReader):
    def __init__(self, rfile, length):
        self._rfile = rfile
        self._remaining = length

    def read(self, size):
        size = min(size, self._remaining)
        if size <= 0:
            return b''

        block = self._rfile.read(size)
        self._remaining -= len(block)
        return block


class ChunkedBodyReader(BodyReader):
    def __init__(self, rfile):
        self._eof = False
        self._rfile = rfile
        self._buffer = b''

    def _get_next_chunk(self):
        while True:
            chunk_size_s = self._rfile.readline()
            logging.debug('chunksz=%r', chunk_size_s)
            if not chunk_size_s:
                raise ConnectionClosedError('Socket closed in the middle of a chunked request')
            if chunk_size_s.strip() != b'':
                break

        chunk_size = int(chunk_size_s, 16)
        if chunk_size == 0:
            self._eof = True
            return b''
        chunk = self._rfile.read(chunk_size)
        logging.debug('chunk=0x%x', len(chunk))
        return chunk

    def read(self, size):
        # be careful not to read more bytes than length
        # in case another request follows on the same connection
        if self._eof:
            return b''

        # this is super-inefficient for large sizes!
        while len(self._buffer) < size:
            chunk = self._get_next_chunk()
            if chunk == b'':
                break
            self._buffer += chunk

        rtn, self._buffer = self._buffer[:size], self._buffer[size:]
        return rtn


class HttpTransport(object):
    def __init__(self, rfile, wfile):
        self._rfile = rfile
        self._wfile = wfile
        self.method = None
        self.path = None
        self.headers = None

    def recv_headers(self):
        self.method, self.path = _process_status(self._rfile)
        self.headers = _process_headers(self._rfile)

    def recv_body(self):
        if b'chunked' in self.headers.get(b'transfer-encoding', b''):
            return ChunkedBodyReader(self._rfile)
        else:
            length = int(self.headers.get(b'content-length', b'-1'))
            return ContentLengthBodyReader(self._rfile, length)

    def send_headers(self, status='200 OK', content_type='text/plain'):
        self._wfile.write(b'\r\n'.join((
            b'HTTP/1.1 ' + status.encode("utf-8"),
            b'Server: ipp-server',
            b'Content-Type: ' + content_type.encode("utf-8"),
            b'Connection: close',
            b'',
            b'')))
        self._wfile.flush()

    def send_body(self, fileobject):
        while True:
            block = fileobject.read(1024)
            if block == b'':
                break
            self._wfile.write(block)
        self._wfile.flush()

    def close(self):
        self._wfile.close()
