from __future__ import division
from __future__ import absolute_import
from __future__ import print_function


class PPD(object):
    def text(self):
        raise NotImplementedError()


class BasicPostscriptPPD(PPD):
    product = 'ipp-server'
    manufacturer = 'h2g2bob'
    model = 'ipp-server-postscript'

    def text(self):
        return b'''*PPD-Adobe: "4.3"

*%% This is a minimal config file
*%% and is almost certainly missing lots of features

*%%     ___________
*%%    |           |
*%%    | PPD File. |
*%%    |           |
*%%  (============(@|
*%%  |            | |
*%%  | [        ] | |
*%%  |____________|/
*%%

*%% About this PPD file
*LanguageLevel: "2"
*LanguageEncoding: ISOLatin1
*LanguageVersion: English
*PCFileName: "%(ppdfilename)s"

*%% Basic capabilities of the device
*FileSystem: False

*%% Printer name
*Product: "%(product)s"
*Manufacturer:  "%(manufacturer)s"
*ModelName: "%(model)s"

*%% Color
*ColorDevice: True
*DefaultColorSpace: CMYK
*Throughput: "1"
*Password: "0"
''' % \
{
    b"product": self.product.encode("ascii"),
    b"manufacturer": self.manufacturer.encode("ascii"),
    b"model": self.model.encode("ascii"),
    b"ppdfilename": b"%s%s" % (self.model.encode("ascii"), b'.ppd')
}


class BasicPdfPPD(BasicPostscriptPPD):
    model = 'ipp-server-pdf'

    def text(self):
        return super(BasicPdfPPD, self).text() + b'''
*% The printer can only handle PDF files, so get CUPS to send that
*% https://en.wikipedia.org/wiki/CUPS#Filter_system
*% https://www.cups.org/doc/spec-ppd.html
*cupsFilter2: "application/pdf application/vnd.cups-pdf 0 pdftopdf"
*cupsFilter2: "application/postscript application/vnd.cups-pdf 50 pstopdf"
'''
