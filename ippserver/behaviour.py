from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import logging
import os.path
import subprocess
import uuid
import random

from .logic import get_job_id
from .logic import OperationEnum
from .logic import JobStateEnum
from .logic import StatusCodeEnum
from .logic import minimal_attributes
from .logic import printer_list_attributes
from .logic import print_job_attributes
from .logic import printer_uptime
from .request import IppRequest

def read_in_blocks(postscript_file):
	while True:
		block = postscript_file.read(1024)
		if block == b'':
			break
		else:
			yield block


class Behaviour(object):
	"""Do anything in response to IPP requests"""
	version=(1, 1)

	def expect_page_data_follows(self, ipp_request):
		return ipp_request.opid_or_status == OperationEnum.print_job


	def handle_ipp(self, ipp_request, postscript_file):
		command_function = self.get_handle_command_function(ipp_request.opid_or_status)
		logging.info('IPP %r -> %r', ipp_request.opid_or_status, command_function)
		return command_function(ipp_request, postscript_file)

	def get_handle_command_function(self, opid_or_status):
		raise NotImplementedError()

class AllCommandsReturnNotImplemented(Behaviour):
	"""A printer which responds to all commands with a not implemented error.

	There's no real use for this, it's just an example.
	"""
	def get_handle_command_function(self, _opid_or_status):
		return self.operation_not_implemented_response

	def operation_not_implemented_response(self, req, _psfile):
		attributes = minimal_attributes()
		return IppRequest(
			self.version,
			StatusCodeEnum.server_error_operation_not_supported,
			req.request_id,
			attributes)

class StatelessPrinter(Behaviour):
	"""A minimal printer which implements all the things a printer needs to work.

	The printer calls handle_postscript() for each print job.
	It says all print jobs succeed immediately: there are some stub functions like create_job() which subclasses could use to keep track of jobs, eg: if operation_get_jobs_response wants to return something sensible.
	"""

	def get_handle_command_function(self, opid_or_status):
		commands = {
			OperationEnum.get_printer_attributes: self.operation_printer_list_response,
			OperationEnum.cups_list_all_printers: self.operation_printer_list_response,
			OperationEnum.cups_get_default: self.operation_printer_list_response,
			OperationEnum.validate_job: self.operation_validate_job_response,
			OperationEnum.get_jobs: self.operation_get_jobs_response,
			OperationEnum.get_job_attrbutes: self.operation_get_job_attributes_response,
			OperationEnum.print_job: self.operation_print_job_response,
			0x0d0a: self.operation_misidentified_as_http,
		}

		try:
			command_function = commands[opid_or_status]
		except KeyError:
			logging.warn('Operation not supported 0x%04x', opid_or_status)
			command_function = operation_not_implemented_response
		return command_function


	def operation_not_implemented_response(self, req, _psfile):
		attributes = minimal_attributes()
		return IppRequest(
			self.version,
			# StatusCodeEnum.server_error_operation_not_supported,
			StatusCodeEnum.server_error_internal_error,
			req.request_id,
			attributes)

	def operation_printer_list_response(self, req, _psfile):
		attributes = printer_list_attributes()
		return IppRequest(
			self.version,
			StatusCodeEnum.ok,
			req.request_id,
			attributes)

	def operation_validate_job_response(self, req, _psfile):
		# TODO this just pretends it's ok!
		attributes = minimal_attributes()
		return IppRequest(
			self.version,
			StatusCodeEnum.ok,
			req.request_id,
			attributes)

	def operation_get_jobs_response(self, req, _psfile):
		# an empty list of jobs, which probably breaks the rfc
		# if the client asked for completed jobs
		# https://tools.ietf.org/html/rfc2911#section-3.2.6.2
		attributes = minimal_attributes()
		return IppRequest(
			self.version,
			StatusCodeEnum.ok,
			req.request_id,
			attributes)

	def operation_print_job_response(self, req, psfile):
		job_id = self.create_job(req)
		attributes = print_job_attributes(job_id, new_job=True)
		self.handle_postscript(req, psfile)
		return IppRequest(
			self.version,
			StatusCodeEnum.ok,
			req.request_id,
			attributes)

	def operation_get_job_attributes_response(self, req, _psfile):
		# Should have all these attributes:
		# https://tools.ietf.org/html/rfc2911#section-4.3

		job_id = get_job_id(req)
		attributes = print_job_attributes(job_id, new_job=False)
		return IppRequest(
			self.version,
			StatusCodeEnum.ok,
			req.request_id,
			attributes)

	def operation_misidentified_as_http(self, _req, _psfile):
		raise Exception("The opid for this operation is \\r\\n, which suggests the request was actually a http request.")

	def create_job(self, req):
		"""Return a job id.

		The StatelessPrinter does not care about the id, but perhaps
		it can be subclassed into something that keeps track of jobs.
		"""
		job_id = random.randint(1,9999)
		return job_id

	def handle_postscript(self, ipp_request, postscript_file):
		raise NotImplementedError


class SaveFilePrinter(StatelessPrinter):
	def __init__(self, directory):
		self.directory = directory
		super(SaveFilePrinter, self).__init__()

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


class RunCommandPrinter(StatelessPrinter):
	def __init__(self, command):
		self.command = command
		super(RunCommandPrinter, self).__init__()

	def handle_postscript(self, _ipp_request, postscript_file):
		logging.info('Running command for job')
		proc = subprocess.Popen(
			self.command,
			stdin=subprocess.PIPE)
		data = b''.join(read_in_blocks(postscript_file))
		proc.communicate(data)
		if proc.returncode:
			raise Exception('The command %r exited with code %r', command, proc.returncode)

