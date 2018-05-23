from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import logging
import importlib
import sys, os.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.version_info[0] < 3:
	__package__ = b"ippserver"
else:
	__package__ = "ippserver"


from . import behaviour
from .pc2paper import Pc2Paper
from .server import run_server, ThreadedTCPServer, ThreadedTCPRequestHandler


def parse_args(args=None):
	pdf_help = 'Request that CUPs sends the document as a PDF file, instead of a PS file. CUPs detects this setting when ADDING a printer: you may need to re-add the printer on a different port'

	parser = argparse.ArgumentParser(description='An IPP server')
	parser.add_argument('-v', '--verbose', action='count', help='Add debugging')
	parser.add_argument('-H', '--host', type=str, default='localhost', metavar='HOST', help='Address to listen on')
	parser.add_argument('-p', '--port', type=int, required=True, metavar='PORT', help='Port to listen on')

	parser_action = parser.add_subparsers(help='Actions', dest='action')

	parser_save = parser_action.add_parser('save', help='Write any print jobs to disk')
	parser_save.add_argument('--pdf', action='store_true', default=False, help=pdf_help)
	parser_save.add_argument('directory', metavar='DIRECTORY', help='Directory to save files into')

	parser_command = parser_action.add_parser('run', help='Run a command when recieving a print job')
	parser_command.add_argument('command', nargs=argparse.REMAINDER, metavar='COMMAND', help='Command to run')
	parser_command.add_argument('--pdf', action='store_true', default=False, help=pdf_help)
	parser_command.add_argument('--env', action='store_true', default=False, help="Store Job attributes in environment (IPP_JOB_ATTRIBUTES)")

	parser_saverun = parser_action.add_parser('saveandrun', help='Write any print jobs to disk and the run a command on them')
	parser_saverun.add_argument('--pdf', action='store_true', default=False, help=pdf_help)
	parser_saverun.add_argument('--env', action='store_true', default=False, help="Store Job attributes in environment (IPP_JOB_ATTRIBUTES)")
	parser_saverun.add_argument('directory', metavar='DIRECTORY', help='Directory to save files into')
	parser_saverun.add_argument('command', nargs=argparse.REMAINDER, metavar='COMMAND', help='Command to run (the filename will be added at the end)')

	parser_command = parser_action.add_parser('reject', help='Respond to all print jobs with job-canceled-at-device')

	parser_command = parser_action.add_parser('pc2paper', help='Post print jobs using http://www.pc2paper.org/')
	parser_command.add_argument('--pdf', action='store_true', default=False, help=pdf_help)
	parser_command.add_argument('--config', metavar='CONFIG', help='File containing an address to send to, in json format')
	parser_loader = parser_action.add_parser('load', help='Load own behaviour')
	parser_loader.add_argument('path', nargs=1, metavar=['PATH'], help='Module implementing behaviour')
	parser_loader.add_argument('command', nargs=argparse.REMAINDER, metavar='COMMAND', help='Arguments for the module')

	return parser.parse_args(args)

def behaviour_from_parsed_args(args):
	if args.action == 'save':
		return behaviour.SaveFilePrinter(
			directory=args.directory,
			filename_ext='pdf' if args.pdf else 'ps')
	if args.action == 'run':
		return behaviour.RunCommandPrinter(
			command=args.command,
			use_env=args.env,
			filename_ext='pdf' if args.pdf else 'ps')
	if args.action == 'saveandrun':
		return behaviour.SaveAndRunPrinter(
			command=args.command,
			use_env=args.env,
			directory=args.directory,
			filename_ext='pdf' if args.pdf else 'ps')
	if args.action == 'pc2paper':
		pc2paper_config = Pc2Paper.from_config_file(args.config)
		return behaviour.PostageServicePrinter(
			service_api=pc2paper_config,
			filename_ext='pdf' if args.pdf else 'ps')
	if args.action == 'load':
		module, name = args.path[0].rsplit(".", 1)
		return getattr(importlib.import_module(module), name)(*args.command)
	if args.action == 'reject':
		return behaviour.RejectAllPrinter()
	raise RuntimeError(args)

def main(args=None):
	parsed_args = parse_args(args)
	logging.basicConfig(level=logging.DEBUG if parsed_args.verbose else logging.INFO)

	server = ThreadedTCPServer(
		(parsed_args.host, parsed_args.port),
		ThreadedTCPRequestHandler,
		behaviour_from_parsed_args(parsed_args))
	run_server(server)

if __name__ == "__main__":
	main()
