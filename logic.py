from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import logging
import time

from .request import IppRequest
from .request import SectionEnum, TagEnum
from . import parsers

VERSION=(1, 1)

class StatusCodeEnum(object):
	ok = 0x0000
	server_error_internal_error = 0x0500
	server_error_operation_not_supported = 	0x0501


class OperationEnum(object):
	get_printer_attributes = 0x000b

	# 0x4000 - 0xFFFF is for extensions
	# CUPS extensions listed here: http://uw714doc.sco.com/en/cups/ipp.html
	cups_list_all_printers = 0x4002

def respond(req):
	if req.opid_or_status == OperationEnum.get_printer_attributes:
		logging.warn('TODO implement get printer attributes')
		return operation_not_implemented_response(req)
	elif req.opid_or_status == OperationEnum.cups_list_all_printers:
		return operation_printer_list_response(req)
	else:
		logging.info('Operation not supported 0x%04x', req.opid_or_status)
		return operation_not_implemented_response(req)


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
		(SectionEnum.printer, b'printer-uri-supported', TagEnum.uri) : [b'ipp://localhost:9000/printer'], # XXX
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
				0x0002, # print-job
				0x000b, # get-printer-attributes
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
		(SectionEnum.printer, b'printer-up-time', TagEnum.integer) : [parsers.Integer(int(time.time())).bytes()],
		(SectionEnum.printer, b'compression-supported', TagEnum.keyword) : [b'none'],
	}
	attr.update(minimal_attributes())
	return attr
