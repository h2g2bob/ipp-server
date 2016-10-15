from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import logging


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
