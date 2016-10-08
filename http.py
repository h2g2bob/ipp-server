from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import re
import os
import os.path

def read_http(f):
	first_line = f.readline()
	m = re.compile(r'^(GET|POST) (/[^ ]*) HTTP/').search(first_line)
	if m is None:
		raise ValueError('Invalid request: %r' % (first_line,))
	while True:
		line = f.readline()
		if line.rstrip(b'\r\n') == '':
			break
	return m.groups()

def write_http(f):
	f.write(b'\r\n'.join((
		b'HTTP/1.1 200 OK',
		b'Server: ipp-server',
		b'',
		b'')))

def write_http_error(f):
	write_http_page(f, 500, b'text/plain', b'There was an error.')

def write_http_hello(f):
	write_http_page(f, 200, b'text/plain', b'This is h2g2bob\'s ipp-server.py')

def write_http_ppd(f):
	with open(local_file_location('ipp-server.ppd'), 'r') as ipp_file:
		write_http_page(f, 200, b'text/plain', ipp_file.read())

def write_http_missing(f):
	write_http_page(f, 404, b'text/plain', b'Page does not exist')

def write_http_page(f, code, content, body):
	code_msg = {200 : 'OK', 500 : 'Server Error', 404 : 'Not found'}[code]
	f.write(b'\r\n'.join((
		b'HTTP/1.1 %d %s' % (code, code_msg,),
		b'Server: ipp-server',
		b'Content-type: %s' % (content,),
		b'Content-length: %d' % (len(body),),
		b'',
		body,
		b'')))

def local_file_location(filename):
	return os.path.join(os.path.dirname(__file__), filename)
