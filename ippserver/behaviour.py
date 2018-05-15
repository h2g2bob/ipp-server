from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import logging
import os.path
import random
import subprocess
import time
import uuid

from . import parsers
from .constants import JobStateEnum
from .constants import OperationEnum
from .constants import StatusCodeEnum
from .ppd import BasicPostscriptPPD, BasicPdfPPD
from .request import IppRequest
from .request import SectionEnum, TagEnum


def get_job_id(req):
	return parsers.Integer.from_bytes(req.only(SectionEnum.operation, 'job-id', TagEnum.integer)).integer


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
	base_uri=b'ipp://localhost:1234/'
	printer_uri=b'ipp://localhost:1234/printer'

	def __init__(self, ppd=BasicPostscriptPPD()):
		self.ppd = ppd

	def expect_page_data_follows(self, ipp_request):
		return ipp_request.opid_or_status == OperationEnum.print_job


	def handle_ipp(self, ipp_request, postscript_file):
		command_function = self.get_handle_command_function(ipp_request.opid_or_status)
		logging.debug('IPP %r -> %r', ipp_request.opid_or_status, command_function)
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
		attributes = self.minimal_attributes()
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
		attributes = self.minimal_attributes()
		return IppRequest(
			self.version,
			# StatusCodeEnum.server_error_operation_not_supported,
			StatusCodeEnum.server_error_internal_error,
			req.request_id,
			attributes)

	def operation_printer_list_response(self, req, _psfile):
		attributes = self.printer_list_attributes()
		return IppRequest(
			self.version,
			StatusCodeEnum.ok,
			req.request_id,
			attributes)

	def operation_validate_job_response(self, req, _psfile):
		# TODO this just pretends it's ok!
		attributes = self.minimal_attributes()
		return IppRequest(
			self.version,
			StatusCodeEnum.ok,
			req.request_id,
			attributes)

	def operation_get_jobs_response(self, req, _psfile):
		# an empty list of jobs, which probably breaks the rfc
		# if the client asked for completed jobs
		# https://tools.ietf.org/html/rfc2911#section-3.2.6.2
		attributes = self.minimal_attributes()
		return IppRequest(
			self.version,
			StatusCodeEnum.ok,
			req.request_id,
			attributes)

	def operation_print_job_response(self, req, psfile):
		job_id = self.create_job(req)
		attributes = self.print_job_attributes(job_id, JobStateEnum.pending, [b'job-incoming', b'job-data-insufficient'])
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
		attributes = self.print_job_attributes(job_id, JobStateEnum.completed, [b'none'])
		return IppRequest(
			self.version,
			StatusCodeEnum.ok,
			req.request_id,
			attributes)

	def operation_misidentified_as_http(self, _req, _psfile):
		raise Exception("The opid for this operation is \\r\\n, which suggests the request was actually a http request.")

	def minimal_attributes(self):
		return {
			# This list comes from
			# https://tools.ietf.org/html/rfc2911
			# Section 3.1.4.2 Response Operation Attributes
			(SectionEnum.operation, b'attributes-charset', TagEnum.charset) : [b'utf-8'],
			(SectionEnum.operation, b'attributes-natural-language', TagEnum.natural_language) : [b'en'],
		}

	def printer_list_attributes(self):
		attr = {
			# rfc2911 section 4.4
			(SectionEnum.printer, b'printer-uri-supported', TagEnum.uri) : [self.printer_uri],
			(SectionEnum.printer, b'uri-authentication-supported', TagEnum.keyword) : [b'none'],
			(SectionEnum.printer, b'uri-security-supported', TagEnum.keyword) : [b'none'],
			(SectionEnum.printer, b'printer-name', TagEnum.name_without_language) : [b'ipp-printer.py'],
			(SectionEnum.printer, b'printer-info', TagEnum.text_without_language) : [b'Printer using ipp-printer.py'],
			(SectionEnum.printer, b'printer-make-and-model', TagEnum.text_without_language) : [b'h2g2bob\'s ipp-printer.py 0.00'],
			(SectionEnum.printer, b'printer-state', TagEnum.enum) : [parsers.Enum(3).bytes()], # XXX 3 is idle
			(SectionEnum.printer, b'printer-state-reasons', TagEnum.keyword) : [b'none'],
			(SectionEnum.printer, b'ipp-versions-supported', TagEnum.keyword) : [b'1.1'],
			(SectionEnum.printer, b'operations-supported', TagEnum.enum) : [
				parsers.Enum(x).bytes()
				for x in (
					OperationEnum.print_job,  # (required by cups)
					OperationEnum.validate_job,  # (required by cups)
					OperationEnum.cancel_job,  # (required by cups)
					OperationEnum.get_job_attrbutes,  # (required by cups)
					OperationEnum.get_printer_attributes,
				)],
			(SectionEnum.printer, b'multiple-document-jobs-supported', TagEnum.boolean) : [parsers.Boolean(False).bytes()],
			(SectionEnum.printer, b'charset-configured', TagEnum.charset) : [b'utf-8'],
			(SectionEnum.printer, b'charset-supported', TagEnum.charset) : [b'utf-8'],
			(SectionEnum.printer, b'natural-language-configured', TagEnum.natural_language) : [b'en'],
			(SectionEnum.printer, b'generated-natural-language-supported', TagEnum.natural_language) : [b'en'],
			(SectionEnum.printer, b'document-format-default', TagEnum.mime_media_type) : [b'application/pdf'],
			(SectionEnum.printer, b'document-format-supported', TagEnum.mime_media_type) : [b'application/pdf'],
			(SectionEnum.printer, b'printer-is-accepting-jobs', TagEnum.boolean) : [parsers.Boolean(True).bytes()],
			(SectionEnum.printer, b'queued-job-count', TagEnum.integer) : [parsers.Integer(0).bytes()],
			(SectionEnum.printer, b'pdl-override-supported', TagEnum.keyword) : [b'not-attempted'],
			(SectionEnum.printer, b'printer-up-time', TagEnum.integer) : [parsers.Integer(self.printer_uptime()).bytes()],
			(SectionEnum.printer, b'compression-supported', TagEnum.keyword) : [b'none'],
		}
		attr.update(self.minimal_attributes())
		return attr

	def print_job_attributes(self, job_id, state, state_reasons):
		# state reasons come from rfc2911 section 4.3.8
		job_uri = b'%sjob/%s' % (self.base_uri, parsers.Integer(job_id).bytes(),)

		attr = {
			# Required for print-job:

			(SectionEnum.operation, b'job-uri', TagEnum.uri): [job_uri],
			(SectionEnum.operation, b'job-id', TagEnum.integer): [parsers.Integer(int(job_id)).bytes()],
			(SectionEnum.operation, b'job-state', TagEnum.enum): [parsers.Enum(state).bytes()],
			(SectionEnum.operation, b'job-state-reasons', TagEnum.keyword): state_reasons,

			# Required for get-job-attributes:

			(SectionEnum.operation, b'job-printer-uri', TagEnum.uri): [self.printer_uri],
			(SectionEnum.operation, b'job-name', TagEnum.name_without_language) : [b'Print job %s' % parsers.Integer(job_id).bytes()],
			(SectionEnum.operation, b'job-originating-user-name', TagEnum.name_without_language) : [b'job-originating-user-name'],
			(SectionEnum.operation, b'time-at-creation', TagEnum.integer) : [parsers.Integer(int(0)).bytes()],
			(SectionEnum.operation, b'time-at-processing', TagEnum.integer) : [parsers.Integer(int(0)).bytes()],
			(SectionEnum.operation, b'time-at-completed', TagEnum.integer) : [parsers.Integer(int(0)).bytes()],
			(SectionEnum.operation, b'job-printer-up-time', TagEnum.integer) : [parsers.Integer(self.printer_uptime()).bytes()],

		}
		attr.update(self.minimal_attributes())
		return attr

	def printer_uptime(self):
		return int(time.time())

	def create_job(self, req):
		"""Return a job id.

		The StatelessPrinter does not care about the id, but perhaps
		it can be subclassed into something that keeps track of jobs.
		"""
		job_id = random.randint(1,9999)
		return job_id

	def handle_postscript(self, ipp_request, postscript_file):
		raise NotImplementedError


class RejectAllPrinter(StatelessPrinter):
	"""A printer that rejects all the print jobs it recieves.

	Cups ignores the rejection notice. I suspect this is because the
	communication is:
		recv http post headers
		recv ipp print_job
		send http continue headers
		recv data
		send ipp aborted

	But to be effective, I suspect the errors need to be sent before the
	http continue:
		recv http post headers
		recv ipp print_job
		send http headers
		send ipp aborted
	"""

	def operation_print_job_response(self, req, _psfile):
		job_id = self.create_job(req)
		attributes = self.print_job_attributes(job_id, JobStateEnum.aborted, [b'job-canceled-at-device'])
		return IppRequest(
			self.version,
			StatusCodeEnum.server_error_job_canceled,
			req.request_id,
			attributes)

	def operation_get_job_attributes_response(self, req, _psfile):
		job_id = get_job_id(req)
		attributes = self.print_job_attributes(job_id, JobStateEnum.aborted, [b'job-canceled-at-device'])
		return IppRequest(
			self.version,
			StatusCodeEnum.server_error_job_canceled,
			req.request_id,
			attributes)


class SaveFilePrinter(StatelessPrinter):
	def __init__(self, directory, filename_ext):
		self.directory = directory
		self.filename_ext = filename_ext

		ppd = {
			'ps': BasicPostscriptPPD(),
			'pdf': BasicPdfPPD(),
		}[filename_ext]

		super(SaveFilePrinter, self).__init__(ppd=ppd)

	def handle_postscript(self, ipp_request, postscript_file):
		filename = self.filename(ipp_request)
		logging.info('Saving print job as %r', filename)
		with open(filename, 'wb') as diskfile:
			for block in read_in_blocks(postscript_file):
				diskfile.write(block)
		self.run_after_saving(filename)

	def run_after_saving(self, filename):
		pass

	def filename(self, ipp_request):
		leaf = self.leaf_filename(ipp_request)
		return os.path.join(self.directory, leaf)

	def leaf_filename(self, _ipp_request):
		# Possibly use the job name from the ipp_request?
		return 'ipp-server-print-job-%s.%s' % (uuid.uuid1(), self.filename_ext,)


class SaveAndRunPrinter(SaveFilePrinter):
	def __init__(self, directory, filename_ext, command):
		self.command = command
		super(SaveAndRunPrinter, self).__init__(directory=directory, filename_ext=filename_ext)

	def run_after_saving(self, filename):
		subprocess.check_call(self.command + [filename])


class RunCommandPrinter(StatelessPrinter):
	def __init__(self, command, filename_ext):
		self.command = command

		ppd = {
			'ps': BasicPostscriptPPD(),
			'pdf': BasicPdfPPD(),
		}[filename_ext]

		super(RunCommandPrinter, self).__init__(ppd=ppd)

	def handle_postscript(self, _ipp_request, postscript_file):
		logging.info('Running command for job')
		proc = subprocess.Popen(
			self.command,
			stdin=subprocess.PIPE)
		data = b''.join(read_in_blocks(postscript_file))
		proc.communicate(data)
		if proc.returncode:
			raise Exception('The command %r exited with code %r', command, proc.returncode)


class PostageServicePrinter(StatelessPrinter):
	def __init__(self, service_api, filename_ext):
		self.service_api = service_api
		self.filename_ext = filename_ext

		ppd = {
			'ps': BasicPostscriptPPD(),
			'pdf': BasicPdfPPD(),
		}[filename_ext]

		super(PostageServicePrinter, self).__init__(ppd=ppd)

	def handle_postscript(self, _ipp_request, postscript_file):
		filename = b'ipp-server-{}.{}'.format(
			int(time.time()),
			self.filename_ext)
		data = b''.join(read_in_blocks(postscript_file))
		self.service_api.post_pdf_letter(filename, data)
