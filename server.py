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

from . import actions
from . import http
from . import request
from . import logic
from .logic import OperationEnum, get_job_id
from .http_reader import HttpRequest

class ThreadedTCPRequestHandler(SocketServer.StreamRequestHandler):
	def handle(self):
		try:
			httpfile = HttpRequest(self.rfile)
			logging.debug('method=%r path=%r', httpfile.method, httpfile.path)
			if httpfile.method == 'POST':
				http_continue, resp = self.handle_ipp(httpfile)
				http.write_http(
					self.wfile,
					content_type='application/ipp',
					status='100 Continue' if http_continue else '200 OK')
				if http_continue:
					job_id = get_job_id(resp)
					data = httpfile.read(None)
					self.server.action_function(job_id, data)
				resp.to_file(self.wfile)
			elif httpfile.method == 'GET' and httpfile.path == '/':
				http.write_http_hello(self.wfile)
			elif httpfile.method == 'GET' and httpfile.path.endswith('.ppd'):
				http.write_http_ppd(self.wfile)
			elif httpfile.method == 'GET':
				http.write_http_missing(self.wfile)
			else:
				raise Exception('Not supported %r %r' % (httpfile.method, httpfile.path))
		except Exception:
			logging.exception('Failed to parse')
			http.write_http_error(self.wfile)
		self.wfile.flush()

	def handle_ipp(self, httpfile):
		req = request.IppRequest.from_file(httpfile)
		http_continue = req.opid_or_status == OperationEnum.print_job
		logging.debug('Got request %r', req)
		resp = logic.respond(req)
		logging.debug('Using response %r', resp)
		return http_continue, resp

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
	allow_reuse_address = True
	def __init__(self, address, request_handler, action_function):
		self.action_function = action_function
		SocketServer.TCPServer.__init__(self, address, request_handler)  # old style class!

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
	parser.add_argument('--port', type=int, required=True, metavar='PORT', help='Port to listen on')

	parser_action = parser.add_subparsers(help='Actions', dest='action')

	parser_save = parser_action.add_parser('save', help='Write any print jobs to disk')
	parser_save.add_argument('directory', metavar='DIRECTORY', help='Directory to save files into')

	parser_command = parser_action.add_parser('run', help='Run a command when recieving a print job')
	parser_command.add_argument('command', nargs=argparse.REMAINDER, metavar='COMMAND', help='Command to run')

	return parser.parse_args()

def action_function_from_args(args):
	if args.action == 'save':
		return actions.save_to_directory(directory=args.save)
	if args.action == 'run':
		return actions.run_command(command=args.command)
	raise RuntimeError(args)

def main(args):
	logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

	server = ThreadedTCPServer(
		(args.host, args.port),
		ThreadedTCPRequestHandler,
		action_function_from_args(args))
	logging.info('Listening on %r', server.server_address)

	server_thread = threading.Thread(target=server.serve_forever)
	server_thread.daemon = True
	server_thread.start()
	wait_until_ctrl_c()
	logging.info('Ready to shut down')
	server.shutdown()

if __name__ == "__main__":
	main(parse_args())
