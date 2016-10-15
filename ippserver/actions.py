from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import logging
import os
import os.path
import subprocess
import uuid


def save_to_directory(directory):
	def do_save_to_directory(data):
		leaf = 'ipp-server-print-job-%s.ps' % (uuid.uuid1(),)
		filename = os.path.join(directory, leaf)
		with open(filename, 'wb') as diskfile:
			diskfile.write(data)
		logging.info('Data written to %r', filename)
	return do_save_to_directory

def run_command(command):
	def do_run_command(data):
		logging.info('Running command for job')
		proc = subprocess.Popen(
			command,
			stdin=subprocess.PIPE)
		proc.communicate(data)
		if proc.returncode:
			raise Exception('The command %r exited with code %r', command, proc.returncode)
	return do_run_command
