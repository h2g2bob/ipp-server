from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import socket
import threading
import SocketServer
import time
import sys
import logging
import argparse

from . import http
from . import request
from . import logic

class ThreadedTCPRequestHandler(SocketServer.StreamRequestHandler):
	def handle(self):
		try:
			method, path = http.read_http(self.rfile)
			logging.debug('method=%r path=%r', method, path)
			if method == 'POST':
				resp = self.handle_ipp()
				http.write_http(self.wfile)
				resp.to_file(self.wfile)
			elif method == 'GET' and path == '/':
				http.write_http_hello(self.wfile)
			elif method == 'GET' and path.endswith('.ppd'):
				http.write_http_ppd(self.wfile)
			elif method == 'GET':
				http.write_http_missing(self.wfile)
			else:
				raise Exception('Not supported %r %r' % (method, path))
		except Exception:
			logging.exception('Failed to parse')
			http.write_http_error(self.wfile)
		self.wfile.flush()

	def handle_ipp(self):
		req = request.IppRequest.from_file(self.rfile)
		logging.debug('Got request %r', req)
		resp = logic.respond(req)
		logging.debug('Using response %r', resp)
		return resp

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
	allow_reuse_address = True

def wait_until_ctrl_c():
	try:
		while True:
			time.sleep(300)
	except KeyboardInterrupt:
		return

def parse_args():
	parser = argparse.ArgumentParser(description='An IPP server')
	parser.add_argument('-v', '--verbose', action='count', help='Add debugging')
	parser.add_argument('--host', type=str, default='localhost', metavar='HOST', help='Address to listen on')
	parser.add_argument('port', type=int, metavar='PORT', help='Port to listen on')
	return parser.parse_args()

def main(args):
	logging.basicConfig(level=logging.DEBUG)

	server = ThreadedTCPServer((args.host, args.port), ThreadedTCPRequestHandler)
	logging.debug('Listening on %r', server.server_address)

	server_thread = threading.Thread(target=server.serve_forever)
	server_thread.daemon = True
	server_thread.start()
	wait_until_ctrl_c()
	logging.info('Ready to shut down')
	server.shutdown()

if __name__ == "__main__":
	main(parse_args())
