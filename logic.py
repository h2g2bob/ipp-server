from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import logging

from .request import IppRequest
from .request import SectionEnum, TagEnum

VERSION=(1, 1)

class StatusCodeEnum(object):
	server_error_internal_error = 0x0500
	server_error_operation_not_supported = 	0x0501


class OperationEnum(object):
	# 0x4000 - 0xFFFF is for extensions
	# CUPS will send 0x4002 (list all printers) as the first request
	# CUPS extensions listed here: http://uw714doc.sco.com/en/cups/ipp.html
	get_printer_attributes = 0x000b


def respond(req):
	if req.opid_or_status == OperationEnum.get_printer_attributes:
		logging.warn('TODO implement get printer attributes')
		return operation_not_implemented_response(req)
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

def minimal_attributes():
	return {
		# This list comes from
		# https://tools.ietf.org/html/rfc2911
		# Section 3.1.4.2 Response Operation Attributes
		(SectionEnum.printer, b'attributes-charset', TagEnum.charset) : b'utf-8',
		(SectionEnum.printer, b'attributes-natural-language', TagEnum.natural_language) : b'en',
	}
