#! /usr/bin/python
from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import sys, os.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ippserver.http_transport import HttpTransport
from ippserver.constants import OperationEnum, TagEnum, SectionEnum
from ippserver.request import IppRequest

from io import BytesIO
import logging
import unittest

class TestIppRequest(unittest.TestCase):
    printer_discovery_http_prefix = b'POST / HTTP/1.1\r\nContent-Length: 635\r\nContent-Type: application/ipp\r\nHost: localhost\r\nUser-Agent: CUPS/1.5.3\r\nExpect: 100-continue\r\n\r\n'
    printer_discovery = b'\x01\x01@\x02\x00\x00\x00\x01\x01G\x00\x12attributes-charset\x00\x05utf-8H\x00\x1battributes-natural-language\x00\x05en-gbD\x00\x14requested-attributes\x00\x12auth-info-requiredD\x00\x00\x00\ndevice-uriD\x00\x00\x00\x12job-sheets-defaultD\x00\x00\x00\x12marker-change-timeD\x00\x00\x00\rmarker-colorsD\x00\x00\x00\x12marker-high-levelsD\x00\x00\x00\rmarker-levelsD\x00\x00\x00\x11marker-low-levelsD\x00\x00\x00\x0emarker-messageD\x00\x00\x00\x0cmarker-namesD\x00\x00\x00\x0cmarker-typesD\x00\x00\x00\x10printer-commandsD\x00\x00\x00\x10printer-defaultsD\x00\x00\x00\x0cprinter-infoD\x00\x00\x00\x19printer-is-accepting-jobsD\x00\x00\x00\x11printer-is-sharedD\x00\x00\x00\x10printer-locationD\x00\x00\x00\x16printer-make-and-modelD\x00\x00\x00\x0cprinter-nameD\x00\x00\x00\rprinter-stateD\x00\x00\x00\x19printer-state-change-timeD\x00\x00\x00\x15printer-state-reasonsD\x00\x00\x00\x0cprinter-typeD\x00\x00\x00\x15printer-uri-supportedB\x00\x14requesting-user-name\x00\x04user\x03'
    def test_consistency(self):
        msg = IppRequest.from_string(self.printer_discovery)
        self.assertEqual(msg, IppRequest.from_string(msg.to_string()))

    def test_attr_only(self):
        msg = IppRequest.from_string(self.printer_discovery)
        self.assertEqual(msg.only(SectionEnum.operation, b'attributes-charset', TagEnum.charset,), b'utf-8')

    def test_attr_lookup(self):
        msg = IppRequest.from_string(self.printer_discovery)
        self.assertEqual(msg.lookup(SectionEnum.operation, b'attributes-charset', TagEnum.charset,), [b'utf-8'])

    def test_attr_only_noexist(self):
        msg = IppRequest.from_string(self.printer_discovery)
        self.assertRaises(KeyError, msg.only, SectionEnum.operation, b'no-exist', TagEnum.charset)

    def test_attr_lookup_noexist(self):
        msg = IppRequest.from_string(self.printer_discovery)
        self.assertRaises(KeyError, msg.lookup, SectionEnum.operation, b'no-exist', TagEnum.charset)

    def test_parse(self):
        msg = IppRequest.from_string(self.printer_discovery)
        self.assertEqual(msg._attributes, {
            (SectionEnum.operation, b'requested-attributes', TagEnum.keyword): [
                b'auth-info-required',
                b'device-uri',
                b'job-sheets-default',
                b'marker-change-time',
                b'marker-colors',
                b'marker-high-levels',
                b'marker-levels',
                b'marker-low-levels',
                b'marker-message',
                b'marker-names',
                b'marker-types',
                b'printer-commands',
                b'printer-defaults',
                b'printer-info',
                b'printer-is-accepting-jobs',
                b'printer-is-shared',
                b'printer-location',
                b'printer-make-and-model',
                b'printer-name',
                b'printer-state',
                b'printer-state-change-time',
                b'printer-state-reasons',
                b'printer-type',
                b'printer-uri-supported'],
            (SectionEnum.operation, b'attributes-charset', TagEnum.charset): [
                b'utf-8'],
            (SectionEnum.operation, b'attributes-natural-language', TagEnum.natural_language): [
                b'en-gb'],
            (SectionEnum.operation, b'requesting-user-name', TagEnum.name_without_language): [
                b'user']})


class TestPrintTestPage(unittest.TestCase):
    def test_strange_request(self):
        data = b'POST /printers/ipp-printer.py HTTP/1.1\r\nContent-Type: application/ipp\r\nHost: localhost:1234\r\nTransfer-Encoding: chunked\r\nUser-Agent: CUPS/1.7.5 (Linux 3.16.0-4-amd64; x86_64) IPP/2.0\r\nExpect: 100-continue\r\n\r\nbf\r\n\x02\x00\x00\x02\x00\x00\x00\x04\x01G\x00\x12attributes-charset\x00\x05utf-8H\x00\x1battributes-natural-language\x00\x05en-gbE\x00\x0bprinter-uri\x00,ipp://localhost:1234/printers/ipp-printer.pyB\x00\x14requesting-user-name\x00\x04userB\x00\x08job-name\x00\x0e12 - Test page\x03\r\n0\r\n\r\n'
        input = BytesIO(data)
        http_transport = HttpTransport(input, BytesIO())
        http_transport.recv_headers()
        req = IppRequest.from_file(http_transport.recv_body())
        self.assertEqual(req.opid_or_status, OperationEnum.print_job)


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    unittest.main()
