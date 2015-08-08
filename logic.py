from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import logging

from .request import IppRequest

VERSION=(1, 1)

class StatusCodeEnum(object):
	server_error_operation_not_supported = 	0x0501


class OperationEnum(object):
	# 0x4000 - 0xFFFF is for extensions
	# CUPS will send 0x4002 (list all printers) as the first request
	# CUPS extensions listed here: http://uw714doc.sco.com/en/cups/ipp.html
	get_printer_attributes = 0x000b


def respond(req):
	# TODO: this just echos back the IPP request
	# It should reply with something useful here instead
	if req.opid_or_status == OperationEnum.get_printer_attributes:
		logging.warn('TODO implement get printer attributes')
		return operation_not_implemented_response(req)
	else:
		logging.info('Operation not supported 0x%04x', req.opid_or_status)
		return operation_not_implemented_response(req)


def operation_not_implemented_response(req):
	attributes = {}
	return IppRequest(
		VERSION,
		StatusCodeEnum.server_error_operation_not_supported,
		req.request_id,
		attributes)
