from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import logging
import os.path
import subprocess
import uuid

from . import logic
from .logic import get_job_id


def read_in_blocks(postscript_file):
	while True:
		block = postscript_file.read(1024)
		if block == b'':
			break
		else:
			yield block


class Behaviour(object):
	"""Do anything in response to IPP requests"""
	def handle_ipp(self, ipp_request, postscript_file):
		raise NotImplementedError()

class NormalPrinter(Behaviour):
	"""A printer which accepts print jobs"""
	def handle_ipp(self, ipp_request, postscript_file):
		ipp_response = logic.respond(ipp_request)
		if postscript_file is not None:
			self.handle_postscript(ipp_request, postscript_file)
		return ipp_response

	def handle_postscript(self, ipp_request, postscript_file):
		raise NotImplementedError


class SaveFilePrinter(NormalPrinter):
	def __init__(self, directory):
		self.directory = directory
		NormalPrinter.__init__(self)

	def handle_postscript(self, ipp_request, postscript_file):
		filename = self.filename(ipp_request)
		logging.info('Saving print job as %r', filename)
		with open(filename, 'wb') as diskfile:
			for block in read_in_blocks(postscript_file):
				diskfile.write(block)

	def filename(self, ipp_request):
		leaf = self.leaf_filename(ipp_request)
		return os.path.join(self.directory, leaf)

	def leaf_filename(self, _ipp_request):
		# Possibly use the job name from the ipp_request?
		return 'ipp-server-print-job-%s.ps' % (uuid.uuid1(),)


class RunCommandPrinter(NormalPrinter):
	def __init__(self, command):
		self.command = command
		NormalPrinter.__init__(self)

	def handle_postscript(self, _ipp_request, postscript_file):
		logging.info('Running command for job')
		proc = subprocess.Popen(
			self.command,
			stdin=subprocess.PIPE)
		data = b''.join(read_in_blocks(postscript_file))
		proc.communicate(data)
		if proc.returncode:
			raise Exception('The command %r exited with code %r', command, proc.returncode)

