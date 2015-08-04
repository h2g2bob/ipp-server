from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from .request import IppRequest, TagEnum, AttributeValue

import unittest
import logging

class TestIppRequest(unittest.TestCase):
	printer_discovery_http_prefix = b'POST / HTTP/1.1\r\nContent-Length: 635\r\nContent-Type: application/ipp\r\nHost: localhost\r\nUser-Agent: CUPS/1.5.3\r\nExpect: 100-continue\r\n\r\n'
	printer_discovery = b'\x01\x01@\x02\x00\x00\x00\x01\x01G\x00\x12attributes-charset\x00\x05utf-8H\x00\x1battributes-natural-language\x00\x05en-gbD\x00\x14requested-attributes\x00\x12auth-info-requiredD\x00\x00\x00\ndevice-uriD\x00\x00\x00\x12job-sheets-defaultD\x00\x00\x00\x12marker-change-timeD\x00\x00\x00\rmarker-colorsD\x00\x00\x00\x12marker-high-levelsD\x00\x00\x00\rmarker-levelsD\x00\x00\x00\x11marker-low-levelsD\x00\x00\x00\x0emarker-messageD\x00\x00\x00\x0cmarker-namesD\x00\x00\x00\x0cmarker-typesD\x00\x00\x00\x10printer-commandsD\x00\x00\x00\x10printer-defaultsD\x00\x00\x00\x0cprinter-infoD\x00\x00\x00\x19printer-is-accepting-jobsD\x00\x00\x00\x11printer-is-sharedD\x00\x00\x00\x10printer-locationD\x00\x00\x00\x16printer-make-and-modelD\x00\x00\x00\x0cprinter-nameD\x00\x00\x00\rprinter-stateD\x00\x00\x00\x19printer-state-change-timeD\x00\x00\x00\x15printer-state-reasonsD\x00\x00\x00\x0cprinter-typeD\x00\x00\x00\x15printer-uri-supportedB\x00\x14requesting-user-name\x00\x04user\x03'
	def test_consistency(self):
		msg = IppRequest.from_string(self.printer_discovery)
		self.assertEqual(msg, IppRequest.from_string(msg.to_string()))

	def test_attr_lookup(self):
		msg = IppRequest.from_string(self.printer_discovery)
		self.assertEqual(msg.operation.only('attributes-charset').text(), 'utf-8')

	def test_attr_noexist(self):
		msg = IppRequest.from_string(self.printer_discovery)
		self.assertRaises(KeyError, msg.operation.only, 'no-exist')

	def test_section_noexist(self):
		msg = IppRequest.from_string(self.printer_discovery)
		self.assertRaises(KeyError, msg.get_section, 0x0f)

	def test_parse(self):
		msg = IppRequest.from_string(self.printer_discovery)
		self.assertEqual(msg.operation._attributes, {
			'requested-attributes': [
				AttributeValue(TagEnum.keyword, 'auth-info-required'),
				AttributeValue(TagEnum.keyword, 'device-uri'),
				AttributeValue(TagEnum.keyword, 'job-sheets-default'),
				AttributeValue(TagEnum.keyword, 'marker-change-time'),
				AttributeValue(TagEnum.keyword, 'marker-colors'),
				AttributeValue(TagEnum.keyword, 'marker-high-levels'),
				AttributeValue(TagEnum.keyword, 'marker-levels'),
				AttributeValue(TagEnum.keyword, 'marker-low-levels'),
				AttributeValue(TagEnum.keyword, 'marker-message'),
				AttributeValue(TagEnum.keyword, 'marker-names'),
				AttributeValue(TagEnum.keyword, 'marker-types'),
				AttributeValue(TagEnum.keyword, 'printer-commands'),
				AttributeValue(TagEnum.keyword, 'printer-defaults'),
				AttributeValue(TagEnum.keyword, 'printer-info'),
				AttributeValue(TagEnum.keyword, 'printer-is-accepting-jobs'),
				AttributeValue(TagEnum.keyword, 'printer-is-shared'),
				AttributeValue(TagEnum.keyword, 'printer-location'),
				AttributeValue(TagEnum.keyword, 'printer-make-and-model'),
				AttributeValue(TagEnum.keyword, 'printer-name'),
				AttributeValue(TagEnum.keyword, 'printer-state'),
				AttributeValue(TagEnum.keyword, 'printer-state-change-time'),
				AttributeValue(TagEnum.keyword, 'printer-state-reasons'),
				AttributeValue(TagEnum.keyword, 'printer-type'),
				AttributeValue(TagEnum.keyword, 'printer-uri-supported')],
			'attributes-charset': [
				AttributeValue(TagEnum.charset, 'utf-8')],
			'attributes-natural-language': [
				AttributeValue(TagEnum.natural_language, 'en-gb')],
			'requesting-user-name': [
				AttributeValue(TagEnum.name_without_language, 'user')]})


if __name__=='__main__':
	logging.getLogger().setLevel(logging.DEBUG)
	unittest.main()
