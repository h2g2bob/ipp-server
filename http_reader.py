from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from abc import ABCMeta, abstractmethod
import re
import logging

class AbstractFile(object):
	__metaclass__ = ABCMeta

	@abstractmethod
	def read(self, size):
		raise NotImplementedError()


class DeChunk(AbstractFile):
	def __init__(self, f):
		self._f = f
		self._buffer = ''

	def read(self, size):
		# XXX this is super-inefficient for large sizes!
		while size is None or len(self._buffer) < size:
			chunk_size_s = self._f.readline()
			logging.debug('chunksz=%r', chunk_size_s)
			if not chunk_size_s:
				logging.warn('Socket closed in the middle of a chunked request')
				break
			if chunk_size_s.strip() == '':
				continue
			chunk_size = int(chunk_size_s, 16)
			if chunk_size == 0:
				break
			chunk = self._f.read(chunk_size)
			logging.debug('chunk=0x%x', len(chunk))
			self._buffer += chunk
		if size is None:
			rtn, self._buffer = self._buffer, ''
		else:
			rtn, self._buffer = self._buffer[:size], self._buffer[size:]
		return rtn


class HttpRequest(AbstractFile):
	def __init__(self, f):
		self.method, self.path = self._process_status(f)
		headers = self._process_headers(f)
		if 'chunked' in headers.get('transfer-encoding', ''):
			f = DeChunk(f)
		self._f = f

	def read(self, size):
		return self._f.read(size)

	@staticmethod
	def _process_status(f):
		first_line = f.readline()
		m = re.compile(r'^(GET|POST) (/[^ ]*) HTTP/').search(first_line)
		if m is None:
			raise ValueError('Invalid request: %r' % (first_line,))
		return m.groups()

	@staticmethod
	def _process_headers(f):
		headers = {}
		while True:
			line = f.readline()
			if line.rstrip(b'\r\n') == '':
				break
			try:
				key, value = line.split(':', 1)
				headers[key.lower().strip()] = value.strip()
			except ValueError:
				logging.warn('Invalid header %r', line)
		return headers
