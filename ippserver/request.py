from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from io import BytesIO
import logging
import operator
import itertools

from .parsers import read_struct, write_struct

class SectionEnum(object):
	# delimiters (sections)
	SECTIONS              = 0x00
	SECTIONS_MASK         = 0xf0
	operation   = 0x01
	job         = 0x02
	END         = 0x03
	printer     = 0x04
	unsupported = 0x05

	@classmethod
	def is_section_tag(cls, tag):
		return (tag & cls.SECTIONS_MASK) == cls.SECTIONS


class TagEnum(object):
	unsupported_value     = 0x10
	unknown_value         = 0x12
	no_value              = 0x13

	# int types
	integer               = 0x21
	boolean               = 0x22
	enum                  = 0x23

	# string types
	octet_str             = 0x30
	datetime_str          = 0x31
	resolution            = 0x32
	range_of_integer      = 0x33
	text_with_language    = 0x35
	name_with_language    = 0x36

	text_without_language = 0x41
	name_without_language = 0x42
	keyword               = 0x44
	uri                   = 0x45
	uri_scheme            = 0x46
	charset               = 0x47
	natural_language      = 0x48
	mime_media_type       = 0x49


class IppRequest(object):
	def __init__(self, version, opid_or_status, request_id, attributes):
		self.version = version # (major, minor)
		self.opid_or_status = opid_or_status
		self.request_id = request_id
		self._attributes = attributes

	def __cmp__(self, other):
		return self.__eq__(other)

	def __eq__(self, other):
		return type(self) == type(other) or self._attributes == other._attributes

	def __repr__(self):
		return 'IppRequest(%r, 0x%04x, 0x%02x, %r)' % (
			self.version,
			self.opid_or_status,
			self.request_id,
			self._attributes,)

	@classmethod
	def from_string(cls, string):
		return cls.from_file(BytesIO(string))

	@classmethod
	def from_file(cls, f):
		version = read_struct(f, b'>bb') # (major, minor)
		operation_id_or_status_code, request_id = read_struct(f, b'>hi')

		attributes = {}
		current_section = None
		current_name = None
		while True:
			tag, = read_struct(f, b'>B')

			if tag == SectionEnum.END:
				break
			elif SectionEnum.is_section_tag(tag):
				current_section = tag
				current_name = None
			else:
				if current_section is None:
					raise Exception('No section delimiter')

				name_len, = read_struct(f, b'>h')
				if name_len == 0:
					if current_name is None:
						raise Exception('Additional attribute needs a name to follow')
					else:
						# additional attribute, under the same name
						pass
				else:
					current_name = f.read(name_len)

				value_len, = read_struct(f, b'>h')
				value_str = f.read(value_len)
				attributes.setdefault((current_section, current_name, tag), []).append(value_str)

		return cls(version, operation_id_or_status_code, request_id, attributes)

	def to_string(self):
		sio = BytesIO()
		self.to_file(sio)
		return sio.getvalue()

	def to_file(self, f):
		version_major, version_minor = 1, 1
		write_struct(f, b'>bb', version_major, version_minor)
		write_struct(f, b'>hi', self.opid_or_status, self.request_id)
		for section, attrs_in_section in itertools.groupby(sorted(self._attributes.keys()), operator.itemgetter(0)):
			write_struct(f, b'>B', section)
			for key in attrs_in_section:
				_section, name, tag = key
				for i, value in enumerate(self._attributes[key]):
					write_struct(f, b'>B', tag)
					if i == 0:
						write_struct(f, b'>h', len(name))
						f.write(name)
					else:
						write_struct(f, b'>h', 0)
					write_struct(f, b'>h', len(value))
					f.write(value)
		write_struct(f, b'>B', SectionEnum.END)

	def lookup(self, section, name, tag):
		return self._attributes[section, name, tag]

	def only(self, section, name, tag):
		items = self.lookup(section, name, tag)
		if len(items) == 1:
			return items[0]
		elif len(items) == 0:
			raise RuntimeError('self._attributes[%r, %r, %r] is empty list' % (section, name, tag,))
		else:
			raise ValueError('self._attributes[%r, %r, %r] has more than one value' % (section, name, tag,))
