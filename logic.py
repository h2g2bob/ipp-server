from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import logging
import random
import time

from .request import IppRequest
from .request import SectionEnum, TagEnum
from . import parsers

VERSION=(1, 1)

PRINTER_URI=b'ipp://localhost:1234/printer'

class StatusCodeEnum(object):
	ok = 0x0000
	server_error_internal_error = 0x0500
	server_error_operation_not_supported = 	0x0501


class OperationEnum(object):
	# https://tools.ietf.org/html/rfc2911#section-4.4.15
	print_job = 0x0002
	validate_job = 0x0004
	cancel_job = 0x0008
	get_job_attrbutes = 0x0009
	get_jobs = 0x000a
	get_printer_attributes = 0x000b

	# 0x4000 - 0xFFFF is for extensions
	# CUPS extensions listed here:
	# https://web.archive.org/web/20061024184939/http://uw714doc.sco.com/en/cups/ipp.html
	cups_get_default = 0x4001
	cups_list_all_printers = 0x4002

class JobStateEnum(object):
	# https://tools.ietf.org/html/rfc2911#section-4.3.7
	pending = 3
	pending_held = 4
	processing = 5
	processing_stopped = 6
	canceled = 7
	aborted = 8
	completed = 9

def respond(req):
	commands = {
		OperationEnum.get_printer_attributes: operation_printer_list_response,
		OperationEnum.cups_list_all_printers: operation_printer_list_response,
		OperationEnum.cups_get_default: operation_printer_list_response,
		OperationEnum.validate_job: operation_validate_job_response,
		OperationEnum.get_jobs: operation_get_jobs_response,
		OperationEnum.get_job_attrbutes: operation_get_job_attributes_response,
		OperationEnum.print_job: operation_print_job_response,
		0x0d0a: operation_misidentified_as_http,
	}

	try:
		command_function = commands[req.opid_or_status]
	except KeyError:
		logging.warn('Operation not supported 0x%04x', req.opid_or_status)
		command_function = operation_not_implemented_response

	logging.info('IPP %r -> %r', req.opid_or_status, command_function)
	return command_function(req)


def operation_not_implemented_response(req):
	attributes = minimal_attributes()
	return IppRequest(
		VERSION,
		# StatusCodeEnum.server_error_operation_not_supported,
		StatusCodeEnum.server_error_internal_error,
		req.request_id,
		attributes)

def operation_printer_list_response(req):
	attributes = printer_list_attributes()
	return IppRequest(
		VERSION,
		StatusCodeEnum.ok,
		req.request_id,
		attributes)

def operation_validate_job_response(req):
	# TODO this just pretends it's ok!
	attributes = minimal_attributes()
	return IppRequest(
		VERSION,
		StatusCodeEnum.ok,
		req.request_id,
		attributes)

def operation_get_jobs_response(req):
	# an empty list of jobs, which probably breaks the rfc
	# if the client asked for completed jobs
	# https://tools.ietf.org/html/rfc2911#section-3.2.6.2
	attributes = minimal_attributes()
	return IppRequest(
		VERSION,
		StatusCodeEnum.ok,
		req.request_id,
		attributes)

def operation_print_job_response(req):
	job_id = random.randint(1,9999)
	attributes = print_job_attributes(job_id, new_job=True)
	return IppRequest(
		VERSION,
		StatusCodeEnum.ok,
		req.request_id,
		attributes)

def operation_get_job_attributes_response(req):
	# Should have all these attributes:
	# https://tools.ietf.org/html/rfc2911#section-4.3

	job_id = parsers.Integer.from_bytes(req.only(SectionEnum.operation, 'job-id', TagEnum.integer)).integer
	attributes = print_job_attributes(job_id, new_job=False)
	return IppRequest(
		VERSION,
		StatusCodeEnum.ok,
		req.request_id,
		attributes)

def operation_misidentified_as_http(req):
	raise Exception("The opid for this operation is \\r\\n, which suggests the request was actually a http request.")

def minimal_attributes():
	return {
		# This list comes from
		# https://tools.ietf.org/html/rfc2911
		# Section 3.1.4.2 Response Operation Attributes
		(SectionEnum.operation, b'attributes-charset', TagEnum.charset) : [b'utf-8'],
		(SectionEnum.operation, b'attributes-natural-language', TagEnum.natural_language) : [b'en'],
	}

def printer_list_attributes():
	attr = {
		# rfc2911 section 4.4
		(SectionEnum.printer, b'printer-uri-supported', TagEnum.uri) : [PRINTER_URI],
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
		(SectionEnum.printer, b'printer-up-time', TagEnum.integer) : [parsers.Integer(printer_uptime()).bytes()],
		(SectionEnum.printer, b'compression-supported', TagEnum.keyword) : [b'none'],
	}
	attr.update(minimal_attributes())
	return attr

def print_job_attributes(job_id, new_job):
	job_uri = b'ipp://localhost:1234/job/%s' % (job_id,)

	# rfc2911 section 4.3.8
	# state, state_reasons = JobStateEnum.aborted, [b'job-canceled-at-device']

	if new_job:
		state, state_reasons = JobStateEnum.pending, [b'job-incoming', b'job-data-insufficient']
	else:
		state, state_reasons = JobStateEnum.completed, [b'none']

	attr = {
		# Required for print-job:

		(SectionEnum.operation, b'job-uri', TagEnum.uri): [job_uri],
		(SectionEnum.operation, b'job-id', TagEnum.integer): [parsers.Integer(int(job_id)).bytes()],
		(SectionEnum.operation, b'job-state', TagEnum.enum): [parsers.Enum(state).bytes()],
		(SectionEnum.operation, b'job-state-reasons', TagEnum.keyword): state_reasons,

		# Required for get-job-attributes:

		(SectionEnum.operation, b'job-printer-uri', TagEnum.uri): [PRINTER_URI],
		(SectionEnum.operation, b'job-name', TagEnum.name_without_language) : [b'Print job %s' % (job_id,)],
		(SectionEnum.operation, b'job-originating-user-name', TagEnum.name_without_language) : [b'job-originating-user-name'],
		(SectionEnum.operation, b'time-at-creation', TagEnum.integer) : [parsers.Integer(int(0)).bytes()],
		(SectionEnum.operation, b'time-at-processing', TagEnum.integer) : [parsers.Integer(int(0)).bytes()],
		(SectionEnum.operation, b'time-at-completed', TagEnum.integer) : [parsers.Integer(int(0)).bytes()],
		(SectionEnum.operation, b'job-printer-up-time', TagEnum.integer) : [parsers.Integer(printer_uptime()).bytes()],

	}
	attr.update(minimal_attributes())
	return attr

def printer_uptime():
	return int(time.time())
