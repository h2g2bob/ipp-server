from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from cStringIO import StringIO
import struct
import logging

def read_struct(f, fmt):
	sz = struct.calcsize(fmt)
	string = f.read(sz)
	return struct.unpack(fmt, string)

class TagEnum(object):
	# delimiters (sections)
	SECTIONS              = 0x00
	SECTIONS_MASK         = 0xf0
	operation_delimiter   = 0x01
	job_delimiter         = 0x02
	end_delimiter         = 0x03
	printer_delimiter     = 0x04
	unsupported_delimiter = 0x05

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


def is_section_tag(tag):
	return (tag & TagEnum.SECTIONS_MASK) == TagEnum.SECTIONS


class AttributeValue(object):
	def __init__(self, tag, value_str):
		self.tag = tag
		self.value_str = value_str

	def __cmp__(self, other):
		return cmp(type(self), type(other)) or cmp(self.tag, other.tag) or cmp(self.value_str, other.value_str)

	def __repr__(self):
		return 'Attribute(0x%02x, %r)' % (self.tag, self.value_str,)

	def text(self):
		if self.tag in {
			TagEnum.octet_str,
			TagEnum.datetime_str,
			TagEnum.resolution,
			TagEnum.range_of_integer,
			TagEnum.text_with_language,
			TagEnum.name_with_language,
			TagEnum.text_without_language,
			TagEnum.name_without_language,
			TagEnum.keyword,
			TagEnum.uri,
			TagEnum.uri_scheme,
			TagEnum.charset,
			TagEnum.natural_language,
			TagEnum.mime_media_type,
		}:
			return self.value_str


class Section(object):
	def __init__(self, attributes=None):
		self._attributes = attributes if attributes is not None else {}

	def add(self, name, value):
		assert isinstance(value, AttributeValue)
		self._attributes.setdefault(name, []).append(value)

	def lookup(self, name):
		return self._attributes[name]

	def only(self, name):
		value, = self.lookup(name)
		return value

	def __repr__(self):
		return 'Section(%r)' % (self._attributes,)


class IppRequest(object):
	def __init__(self, version, opid_or_status, request_id, sections):
		self.version = version # (major, minor)
		self.opid_or_status = opid_or_status
		self.request_id = request_id
		self._sections = sections

	def get_section(self, section_tag):
		return self._sections[section_tag]

	def get_or_make_section(self, section_tag):
		# XXX not sure if this is a good idea
		assert is_section_tag(section_tag)
		try:
			return self._sections[section_tag]
		except KeyError:
			self._sections[section_tag] = Section()
			return self._sections[section_tag]

	@property
	def operation(self):
		return self.get_section(TagEnum.operation_delimiter)

	@property
	def job(self):
		return self.get_section(TagEnum.job_delimiter)

	@property
	def printer(self):
		return self.get_section(TagEnum.printer_delimiter)

	def __cmp__(self, other):
		return cmp(type(self), type(other)) or cmp(self._attributes, other._attributes)

	def __repr__(self):
		return 'IppRequest(%r)' % (self._attributes,)

	@classmethod
	def from_string(cls, string):
		return cls.from_file(StringIO(string))

	@classmethod
	def from_file(cls, f):
		version = read_struct(f, b'>bb') # (major, minor)
		operation_id_or_status_code, request_id = read_struct(f, b'>hi')

		sections = {}
		current_section = None
		current_name = None
		while True:
			tag, = read_struct(f, b'>B')
			if tag == TagEnum.end_delimiter:
				break
			elif is_section_tag(tag):
				current_section = sections.setdefault(tag, Section())
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
				current_section.add(current_name, AttributeValue(tag, value_str))

		return cls(version, operation_id_or_status_code, request_id, sections)
		

