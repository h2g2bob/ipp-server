from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import json
import logging
import requests
from collections import namedtuple


class Pc2Paper(namedtuple('Pc2Paper',
        ('username', 'password', 'name', 'address1', 'address2', 'address3', 'address4', 'postcode', 'country', 'postage', 'paper', 'envelope', 'extras'))):
    # From https://www.pc2paper.co.uk/downloads/country.csv
    NUMERIC_COUNTRY_CODES = {
        'UK': 1,
    }

    # From http://www.pc2paper.co.uk/datagetpostage.asp?method=getZonesLetterCanBeSentFrom&str=1
    POSTAGE_TYPES = {
        'UK 1st': 3,
        'UK 2nd': 31,
    }

    # From http://www.pc2paper.co.uk/datagetpostage.asp?method=getPaperBasedOnZoneAndPrintType&str=3,Colour%20Laser
    PAPER_TYPES = {
        '80gsm': 4,
        '100gsm': 17,
        'Conqueror': 5,
        '80gsm double sided': 14,
    }

    ENVELOPE_TYPES = {
        'DL': 1,
        'C5': 10,
        'A4': 11,
    }

    @classmethod
    def from_config_file(cls, filename):
        with open(filename) as f:
            data = json.load(f)

        conversions = [
            ('country', cls.NUMERIC_COUNTRY_CODES),
            ('postage', cls.POSTAGE_TYPES),
            ('paper', cls.PAPER_TYPES),
            ('envelope', cls.ENVELOPE_TYPES),
        ]
        for key, lookup in conversions:
            if not isinstance(data[key], int):
                data[key] = lookup[data[key]]

        return cls(**data)

    def post_pdf_letter(self, filename, pdffile):
        pdf_guid = self._upload_pdf(filename, pdffile)
        self._post_letter(pdf_guid)

    def _upload_pdf(self, filename, pdffile):
        post_data = {
            'username': self.username,
            'password': self.password,
            'filename': filename,
            'fileContent': [ord(byte) for byte in pdffile],
        }
        response = requests.post(
            'https://www.pc2paper.co.uk/lettercustomerapi.svc/json/UploadDocument',
            headers={'Content-type': 'application/json'},
            data=json.dumps(post_data))
        response_data = response.json()
        logging.debug('Response to uploading %r is %r', filename, response_data)
        error_messages = response_data['d']['ErrorMessages']
        if error_messages:
            raise ValueError(error_messages)
        return response_data['d']['FileCreatedGUID']

    def _post_letter(self, pdf_guid):
        post_data = {
            'username': self.username,
            'password': self.password,
            'letterForPosting': {
                'SourceClient' : 'h2g2bob ipp-server',
                'Addresses': [{
                    'ReceiverName': self.name,
                    'ReceiverAddressLine1': self.address1,
                    'ReceiverAddressLine2': self.address2,
                    'ReceiverAddressTownCityOrLine3': self.address3,
                    'ReceiverAddressCountyStateOrLine4': self.address4,
                    'ReceiverAddressPostCode': self.postcode,
                }],
                'ReceiverCountryCode': self.country,
                'Postage': self.postage,
                'Paper': self.paper,
                'Envelope': self.envelope,
                'Extras': self.extras,
                # 'LetterBody' : '',
                'FileAttachementGUIDs': [pdf_guid],
            },
        }
        response = requests.post(
            'https://www.pc2paper.co.uk/lettercustomerapi.svc/json/SendSubmitLetterForPosting',
            headers={'Content-type': 'application/json'},
            data=json.dumps(post_data))
        response_data = response.json()

        logging.debug('Response to posting %r is %r', pdf_guid, response_data)
        error_messages = response_data['d']['ErrorMessages']
        if error_messages:
            raise ValueError(error_messages)
