import base64
import os.path
from copy import copy
from decimal import Decimal
from typing import List
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.utils.datetime_safe import date
from lxml import etree
from told_common.data import (
    Afgiftsanmeldelse,
    Afsender,
    Forsendelsestype,
    FragtForsendelse,
    Modtager,
    PostForsendelse,
    Vareafgiftssats,
    Varelinje,
)
from zeep import Transport
from zeep.exceptions import Fault, TransportError
from zeep.wsdl import Document

from admin.clients.prisme import (
    CustomDutyRequest,
    CustomDutyResponse,
    PrismeClient,
    PrismeConnectionException,
    PrismeException,
    PrismeHttpException,
    send_afgiftsanmeldelse,
)


class DummyRequest:
    def __init__(self, requestHeader, xmlCollection):
        self.requestHeader = requestHeader
        self.xmlCollection = xmlCollection


class DummyRequestItem:
    def __init__(self, xml):
        self.xml = xml


class DummyRequestItemList:
    def __init__(self, items):
        self.items = items


class DummyResponseStatus:
    def __init__(self, reply_code, reply_text):
        self.replyCode = reply_code
        self.replyText = reply_text


class DummyErrorResponse:
    def __init__(self, reply_code, reply_text):
        self.status = DummyResponseStatus(reply_code, reply_text)


class DummyResponseItem:
    def __init__(self, code, text, xml):
        self.replyCode = code
        self.replyText = text
        self.xml = xml


class DummyResponseItemList:
    def __init__(self, items):
        self.GWSReplyInstanceDCFUJ = items


class DummyResponse:
    def __init__(self, data: List[DummyResponseItem]):
        self.status = DummyResponseStatus(0, "ok")
        self.instanceCollection = DummyResponseItemList(data)


class PrismeTest(TestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.anmeldelse = Afgiftsanmeldelse(
            id=1,
            fragtforsendelse=FragtForsendelse(
                id=1,
                forsendelsestype=Forsendelsestype.SKIB,
                fragtbrevsnummer=1,
                fragtbrev=ContentFile(
                    b"Testdata (fragtbrev)", "/fragtbreve/1/fragtbrev.txt"
                ),
                forbindelsesnr="123",
                afgangsdato=date(2023, 10, 1),
            ),
            postforsendelse=None,
            afsender=Afsender(
                id=1,
                navn="Testfirma1",
                adresse="Testvej 12",
                postnummer=1234,
                by="Testby",
                postbox=1234,
                telefon="123456",
                cvr=12345678,
            ),
            modtager=Modtager(
                id=1,
                navn="Testfirma2",
                adresse="Testvej 34",
                postnummer=1234,
                by="Testby",
                postbox=1234,
                telefon="123456",
                cvr=12345678,
                kreditordning=True,
                stedkode=700,
            ),
            leverandørfaktura_nummer="5678",
            betales_af="afsender",
            indførselstilladelse="1234",
            betalt=True,
            status="godkendt",
            dato=date(2023, 11, 13),
            toldkategori="73A",
            varelinjer=[
                Varelinje(
                    id=1,
                    afgiftsanmeldelse=1,
                    vareafgiftssats=Vareafgiftssats(
                        id=1,
                        afgiftstabel=1,
                        vareart_da="Testvarer1",
                        vareart_kl="Testvarer1",
                        afgiftsgruppenummer=2,
                        enhed=Vareafgiftssats.Enhed.ANTAL,
                        afgiftssats=Decimal("20.00"),
                        kræver_indførselstilladelse=False,
                        har_privat_tillægsafgift_alkohol=False,
                        minimumsbeløb=None,
                        overordnet=None,
                        segment_nedre=None,
                        segment_øvre=None,
                        subsatser=None,
                    ),
                    mængde=Decimal("42.0"),
                    antal=1,
                    fakturabeløb=Decimal("123.45"),
                    afgiftsbeløb=Decimal("20.00"),
                ),
                Varelinje(
                    id=2,
                    afgiftsanmeldelse=1,
                    vareafgiftssats=Vareafgiftssats(
                        id=2,
                        afgiftstabel=1,
                        vareart_da="Testvarer2",
                        vareart_kl="Testvarer2",
                        afgiftsgruppenummer=2,
                        enhed=Vareafgiftssats.Enhed.ANTAL,
                        afgiftssats=Decimal("120.00"),
                        kræver_indførselstilladelse=False,
                        har_privat_tillægsafgift_alkohol=False,
                        minimumsbeløb=None,
                        overordnet=None,
                        segment_nedre=None,
                        segment_øvre=None,
                        subsatser=None,
                    ),
                    mængde=Decimal("142.0"),
                    antal=1,
                    fakturabeløb=Decimal("1123.45"),
                    afgiftsbeløb=Decimal("120.00"),
                ),
            ],
            beregnet_faktureringsdato=date(2024, 1, 1),
            leverandørfaktura=ContentFile(
                "Testdata (leverandørfaktura)".encode("utf-8"),
                "/leverandørfakturaer/1/leverandørfaktura.txt",
            ),
            afgift_total=Decimal("140.00"),
            notater=[],
            prismeresponses=[],
        )
        cls.anmeldelse2 = Afgiftsanmeldelse(
            id=2,
            fragtforsendelse=FragtForsendelse(
                id=1,
                forsendelsestype=Forsendelsestype.FLY,
                fragtbrevsnummer=1,
                fragtbrev=ContentFile(
                    b"Testdata (fragtbrev)", "/fragtbreve/1/fragtbrev.txt"
                ),
                forbindelsesnr="123",
                afgangsdato=date(2023, 10, 1),
            ),
            postforsendelse=None,
            afsender=Afsender(
                id=1,
                navn="Testfirma1",
                adresse="Testvej 12",
                postnummer=1234,
                by="Testby",
                postbox=1234,
                telefon="123456",
                cvr=12345678,
            ),
            modtager=Modtager(
                id=1,
                navn="Testfirma2",
                adresse="Testvej 34",
                postnummer=1234,
                by="Testby",
                postbox=1234,
                telefon="123456",
                kreditordning=True,
                cvr=None,
            ),
            leverandørfaktura_nummer="5678",
            betales_af="modtager",
            indførselstilladelse="1234",
            betalt=True,
            status="godkendt",
            dato=date(2023, 11, 13),
            toldkategori="73A",
            varelinjer=[
                Varelinje(
                    id=1,
                    afgiftsanmeldelse=1,
                    vareafgiftssats=Vareafgiftssats(
                        id=1,
                        afgiftstabel=1,
                        vareart_da="Testvarer3",
                        vareart_kl="Testvarer3",
                        afgiftsgruppenummer=3,
                        enhed=Vareafgiftssats.Enhed.LITER,
                        afgiftssats=Decimal("20.00"),
                        kræver_indførselstilladelse=False,
                        har_privat_tillægsafgift_alkohol=False,
                        minimumsbeløb=None,
                        overordnet=None,
                        segment_nedre=None,
                        segment_øvre=None,
                        subsatser=None,
                    ),
                    mængde=Decimal("42.0"),
                    antal=1,
                    fakturabeløb=Decimal("123.45"),
                    afgiftsbeløb=Decimal("20.00"),
                ),
                Varelinje(
                    id=2,
                    afgiftsanmeldelse=1,
                    vareafgiftssats=Vareafgiftssats(
                        id=2,
                        afgiftstabel=1,
                        vareart_da="Testvarer4",
                        vareart_kl="Testvarer4",
                        afgiftsgruppenummer=4,
                        enhed=Vareafgiftssats.Enhed.KILOGRAM,
                        afgiftssats=Decimal("120.00"),
                        kræver_indførselstilladelse=False,
                        har_privat_tillægsafgift_alkohol=False,
                        minimumsbeløb=None,
                        overordnet=None,
                        segment_nedre=None,
                        segment_øvre=None,
                        subsatser=None,
                    ),
                    mængde=Decimal("142.0"),
                    antal=1,
                    fakturabeløb=Decimal("1123.45"),
                    afgiftsbeløb=Decimal("120.00"),
                ),
            ],
            beregnet_faktureringsdato=date(2024, 1, 1),
            leverandørfaktura=ContentFile(
                "Testdata (leverandørfaktura)".encode("utf-8"),
                "/leverandørfakturaer/1/leverandørfaktura.txt",
            ),
            afgift_total=Decimal("140.00"),
            notater=[],
            prismeresponses=[],
        )
        cls.anmeldelse3 = Afgiftsanmeldelse(
            id=3,
            postforsendelse=PostForsendelse(
                id=1,
                forsendelsestype=Forsendelsestype.FLY,
                postforsendelsesnummer=5,
                afsenderbykode="800",
                afgangsdato=date(2023, 10, 1),
            ),
            fragtforsendelse=None,
            afsender=Afsender(
                id=1,
                navn="Testfirma1",
                adresse="Testvej 12",
                postnummer=1234,
                by="Testby",
                postbox=1234,
                telefon="123456",
                cvr=12345678,
            ),
            modtager=Modtager(
                id=1,
                navn="Testfirma2",
                adresse="Testvej 34",
                postnummer=1234,
                by="Testby",
                postbox=1234,
                telefon="123456",
                cvr=12345678,
                kreditordning=True,
                stedkode=600,
            ),
            leverandørfaktura_nummer="5678",
            betales_af="afsender",
            indførselstilladelse="1234",
            betalt=True,
            status="godkendt",
            dato=date(2023, 11, 13),
            toldkategori="73A",
            varelinjer=[
                Varelinje(
                    id=1,
                    afgiftsanmeldelse=1,
                    vareafgiftssats=Vareafgiftssats(
                        id=1,
                        afgiftstabel=1,
                        vareart_da="Testvarer1",
                        vareart_kl="Testvarer1",
                        afgiftsgruppenummer=2,
                        enhed=Vareafgiftssats.Enhed.ANTAL,
                        afgiftssats=Decimal("20.00"),
                        kræver_indførselstilladelse=False,
                        har_privat_tillægsafgift_alkohol=False,
                        minimumsbeløb=None,
                        overordnet=None,
                        segment_nedre=None,
                        segment_øvre=None,
                        subsatser=None,
                    ),
                    mængde=Decimal("42.0"),
                    antal=1,
                    fakturabeløb=Decimal("123.45"),
                    afgiftsbeløb=Decimal("20.00"),
                ),
                Varelinje(
                    id=2,
                    afgiftsanmeldelse=1,
                    vareafgiftssats=Vareafgiftssats(
                        id=2,
                        afgiftstabel=1,
                        vareart_da="Testvarer2",
                        vareart_kl="Testvarer2",
                        afgiftsgruppenummer=2,
                        enhed=Vareafgiftssats.Enhed.ANTAL,
                        afgiftssats=Decimal("120.00"),
                        kræver_indførselstilladelse=False,
                        har_privat_tillægsafgift_alkohol=False,
                        minimumsbeløb=None,
                        overordnet=None,
                        segment_nedre=None,
                        segment_øvre=None,
                        subsatser=None,
                    ),
                    mængde=Decimal("142.0"),
                    antal=1,
                    fakturabeløb=Decimal("1123.45"),
                    afgiftsbeløb=Decimal("120.00"),
                ),
            ],
            beregnet_faktureringsdato=date(2024, 1, 1),
            leverandørfaktura=ContentFile(
                "Testdata (leverandørfaktura)".encode("utf-8"),
                "/leverandørfakturaer/1/leverandørfaktura.txt",
            ),
            afgift_total=Decimal("140.00"),
            notater=[],
            prismeresponses=[],
        )

    @staticmethod
    def strip_xml_whitespace(xml: str):
        return etree.tostring(
            etree.XML(xml, parser=etree.XMLParser(remove_blank_text=True))
        )

    def test_request_xml_1(self):
        request = CustomDutyRequest(self.anmeldelse)
        expected = self.strip_xml_whitespace(
            f"""
            <CustomDutyHeader>
              <BillOfLadingOrPostalNumber>1</BillOfLadingOrPostalNumber>
              <ConnectionNumber>123</ConnectionNumber>
              <CustomDutyHeaderLines>
                <CustomDutyHeaderLine>
                  <BillAmount>123.45</BillAmount>
                  <LineAmount>20.00</LineAmount>
                  <LineNum>001</LineNum>
                  <Qty>1</Qty>
                  <TaxGroupNumber>002</TaxGroupNumber>
                </CustomDutyHeaderLine>
              </CustomDutyHeaderLines>
              <CustomDutyHeaderLines>
                <CustomDutyHeaderLine>
                  <BillAmount>1123.45</BillAmount>
                  <LineAmount>120.00</LineAmount>
                  <LineNum>002</LineNum>
                  <Qty>1</Qty>
                  <TaxGroupNumber>002</TaxGroupNumber>
                </CustomDutyHeaderLine>
              </CustomDutyHeaderLines>
              <CustomsCategory>73A</CustomsCategory>
              <CvrConsignee>12345678</CvrConsignee>
              <CvrConsigner>12345678</CvrConsigner>
              <DeliveryDate>2023-10-01</DeliveryDate>
              <DlvModeId>10</DlvModeId>
              <ImportAuthorizationNumber>1234</ImportAuthorizationNumber>
              <LocationCode>700</LocationCode>
              <PaymentParty>Consigner</PaymentParty>
              <TaxNotificationNumber>1</TaxNotificationNumber>
              <Type>TF10</Type>
              <VendInvoiceNumber>5678</VendInvoiceNumber>
              <WebDueDate>2024-01-01</WebDueDate>
              <files>
                <file>
                  <Content>{base64.b64encode("Testdata (leverandørfaktura)".encode("utf-8")).decode("ascii")}</Content>
                  <Name>leverandørfaktura.txt</Name>
                </file>
                <file>
                  <Content>{base64.b64encode("Testdata (fragtbrev)".encode("utf-8")).decode("ascii")}</Content>
                  <Name>fragtbrev.txt</Name>
                </file>
              </files>
            </CustomDutyHeader>
        """
        )
        self.assertEqual(request.reply_class, CustomDutyResponse)
        self.assertEqual(request.leveringsmåde, 10)
        self.assertEqual(request.forsendelse, self.anmeldelse.fragtforsendelse)
        self.assertEqual(request.stedkode, "700")
        self.assertEqual(request.betaler, "Consigner")
        self.assertEqual(request.forsendelsesnummer, 1)
        self.assertEqual(request.forbindelsesnummer, "123")
        self.assertEqual(request.toldkategori, "73A")
        self.assertEqual(self.strip_xml_whitespace(request.xml), expected, request.xml)

    def test_request_xml_2(self):
        request = CustomDutyRequest(self.anmeldelse2)
        expected = self.strip_xml_whitespace(
            f"""
            <CustomDutyHeader>
              <BillOfLadingOrPostalNumber>1</BillOfLadingOrPostalNumber>
              <ConnectionNumber>123</ConnectionNumber>
              <CustomDutyHeaderLines>
                <CustomDutyHeaderLine>
                  <BillAmount>123.45</BillAmount>
                  <LineAmount>20.00</LineAmount>
                  <LineNum>001</LineNum>
                  <Qty>42.0</Qty>
                  <TaxGroupNumber>003</TaxGroupNumber>
                </CustomDutyHeaderLine>
              </CustomDutyHeaderLines>
              <CustomDutyHeaderLines>
                <CustomDutyHeaderLine>
                  <BillAmount>1123.45</BillAmount>
                  <LineAmount>120.00</LineAmount>
                  <LineNum>002</LineNum>
                  <Qty>142.0</Qty>
                  <TaxGroupNumber>004</TaxGroupNumber>
                </CustomDutyHeaderLine>
              </CustomDutyHeaderLines>
              <CustomsCategory>73A</CustomsCategory>
              <CvrConsignee></CvrConsignee>
              <CvrConsigner>12345678</CvrConsigner>
              <DeliveryDate>2023-10-01</DeliveryDate>
              <DlvModeId>40</DlvModeId>
              <ImportAuthorizationNumber>1234</ImportAuthorizationNumber>
              <LocationCode></LocationCode>
              <PaymentParty>Consignee</PaymentParty>
              <TaxNotificationNumber>2</TaxNotificationNumber>
              <Type>TF10</Type>
              <VendInvoiceNumber>5678</VendInvoiceNumber>
              <WebDueDate>2024-01-01</WebDueDate>
              <files>
                <file>
                  <Content>{base64.b64encode("Testdata (leverandørfaktura)".encode("utf-8")).decode("ascii")}</Content>
                  <Name>leverandørfaktura.txt</Name>
                </file>
                <file>
                  <Content>{base64.b64encode("Testdata (fragtbrev)".encode("utf-8")).decode("ascii")}</Content>
                  <Name>fragtbrev.txt</Name>
                </file>
              </files>
            </CustomDutyHeader>
        """
        )
        self.assertEqual(request.reply_class, CustomDutyResponse)
        self.assertEqual(request.leveringsmåde, 40)
        self.assertEqual(request.forsendelse, self.anmeldelse2.fragtforsendelse)
        self.assertEqual(request.stedkode, "")
        self.assertEqual(request.betaler, "Consignee")
        self.assertEqual(request.forsendelsesnummer, 1)
        self.assertEqual(request.forbindelsesnummer, "123")
        self.assertEqual(request.toldkategori, "73A")
        self.assertEqual(self.strip_xml_whitespace(request.xml), expected, request.xml)

    def test_request_xml_3(self):
        request = CustomDutyRequest(self.anmeldelse3)
        expected = self.strip_xml_whitespace(
            f"""
            <CustomDutyHeader>
              <BillOfLadingOrPostalNumber>5</BillOfLadingOrPostalNumber>
              <ConnectionNumber>999</ConnectionNumber>
              <CustomDutyHeaderLines>
                <CustomDutyHeaderLine>
                  <BillAmount>123.45</BillAmount>
                  <LineAmount>20.00</LineAmount>
                  <LineNum>001</LineNum>
                  <Qty>1</Qty>
                  <TaxGroupNumber>002</TaxGroupNumber>
                </CustomDutyHeaderLine>
              </CustomDutyHeaderLines>
              <CustomDutyHeaderLines>
                <CustomDutyHeaderLine>
                  <BillAmount>1123.45</BillAmount>
                  <LineAmount>120.00</LineAmount>
                  <LineNum>002</LineNum>
                  <Qty>1</Qty>
                  <TaxGroupNumber>002</TaxGroupNumber>
                </CustomDutyHeaderLine>
              </CustomDutyHeaderLines>
              <CustomsCategory>73A</CustomsCategory>
              <CvrConsignee>12345678</CvrConsignee>
              <CvrConsigner>12345678</CvrConsigner>
              <DeliveryDate>2023-10-01</DeliveryDate>
              <DlvModeId>50</DlvModeId>
              <ImportAuthorizationNumber>1234</ImportAuthorizationNumber>
              <LocationCode>600</LocationCode>
              <PaymentParty>Consigner</PaymentParty>
              <TaxNotificationNumber>3</TaxNotificationNumber>
              <Type>TF10</Type>
              <VendInvoiceNumber>5678</VendInvoiceNumber>
              <WebDueDate>2024-01-01</WebDueDate>
              <files>
                <file>
                  <Content>{base64.b64encode("Testdata (leverandørfaktura)".encode("utf-8")).decode("ascii")}</Content>
                  <Name>leverandørfaktura.txt</Name>
                </file>
              </files>
            </CustomDutyHeader>
        """
        )
        self.assertEqual(request.reply_class, CustomDutyResponse)
        self.assertEqual(request.leveringsmåde, 50)
        self.assertEqual(request.forsendelse, self.anmeldelse3.postforsendelse)
        self.assertEqual(request.stedkode, "600")
        self.assertEqual(request.betaler, "Consigner")
        self.assertEqual(request.forsendelsesnummer, 5)
        self.assertEqual(request.forbindelsesnummer, "999")
        self.assertEqual(request.toldkategori, "73A")
        self.assertEqual(self.strip_xml_whitespace(request.xml), expected, request.xml)

    def test_request_xml_4(self):
        temp = copy(self.anmeldelse)
        temp.fragtforsendelse = None
        temp.postforsendelse = None
        request = CustomDutyRequest(temp)
        with self.assertRaises(ValueError):
            _ = request.leveringsmåde
        with self.assertRaises(ValueError):
            _ = request.forsendelsesnummer

    @override_settings(ENVIRONMENT="test")
    def test_send_afgiftsanmeldelse_test(self):
        responses = send_afgiftsanmeldelse(self.anmeldelse)
        self.assertEqual(len(responses), 1)
        response = responses[0]
        self.assertTrue(isinstance(response, CustomDutyResponse))
        self.assertEqual(response.record_id, "5637147578")
        self.assertEqual(response.tax_notification_number, "44668899")
        self.assertEqual(response.delivery_date, "2023-04-07T00:00:00")
        self.assertEqual(
            response.xml.replace(" ", ""),
            """
            <CustomDutyTableFUJ>
            <RecId>5637147578</RecId>
            <TaxNotificationNumber>44668899</TaxNotificationNumber>
            <DeliveryDate>2023-04-07T00:00:00</DeliveryDate>
            </CustomDutyTableFUJ>
            """.replace(
                " ", ""
            ),
        )

    @override_settings(ENVIRONMENT="test", PRISME_MOCK_HTTP_ERROR=413)
    def test_send_afgiftsanmeldelse_test_exception(self):
        with self.assertRaises(PrismeHttpException) as cm:
            send_afgiftsanmeldelse(self.anmeldelse)
        exception = cm.exception
        self.assertEqual(
            exception.message,
            "Server returned HTTP status 413\n"
            "Prisme-fejl: Afsendelse er for stor (for store filer vedhæftet)",
        )
        self.assertEqual(exception.code, 413)

    @staticmethod
    def get_type(name: str):
        if name == "tns:GWSRequestDCFUJ":
            return DummyRequest
        if name == "tns:GWSRequestXMLDCFUJ":
            return DummyRequestItem
        if name == "tns:ArrayOfGWSRequestXMLDCFUJ":
            return DummyRequestItemList

    @override_settings(ENVIRONMENT="production")
    @patch.object(PrismeClient, "client")
    def test_send_afgiftsanmeldelse_errorcode(self, mock_client):
        # mock_client.get_type.side_effect = self.get_type
        mock_client.service.processService.return_value = DummyErrorResponse(
            1, "test error"
        )
        with self.assertRaises(PrismeException) as cm:
            send_afgiftsanmeldelse(self.anmeldelse)
        exception = cm.exception
        self.assertEqual(exception.__class__, PrismeException)
        self.assertEqual(exception.code, 1)
        self.assertEqual(exception.message, "test error")

    @override_settings(ENVIRONMENT="production")
    @patch.object(PrismeClient, "client")
    def test_send_afgiftsanmeldelse(self, mock_client):
        mock_client.service.processService.return_value = DummyResponse(
            [
                DummyResponseItem(
                    0,
                    "",
                    """
                <CustomDutyTableFUJ>
                <RecId>111111</RecId>
                <TaxNotificationNumber>1234</TaxNotificationNumber>
                <DeliveryDate>2025-16-18T00:00:00</DeliveryDate>
                </CustomDutyTableFUJ>
            """,
                )
            ]
        )
        responses = send_afgiftsanmeldelse(self.anmeldelse)

        self.assertEqual(len(responses), 1)
        response = responses[0]
        self.assertTrue(isinstance(response, CustomDutyResponse))
        self.assertEqual(response.record_id, "111111")
        self.assertEqual(response.tax_notification_number, "1234")
        self.assertEqual(response.delivery_date, "2025-16-18T00:00:00")
        self.assertEqual(
            response.xml.replace(" ", ""),
            """
            <CustomDutyTableFUJ>
            <RecId>111111</RecId>
            <TaxNotificationNumber>1234</TaxNotificationNumber>
            <DeliveryDate>2025-16-18T00:00:00</DeliveryDate>
            </CustomDutyTableFUJ>
            """.replace(
                " ", ""
            ),
        )

    @override_settings(ENVIRONMENT="production")
    @patch.object(PrismeClient, "client")
    def test_send_afgiftsanmeldelse_error_in_object(self, mock_client):
        mock_client.service.processService.return_value = DummyResponse(
            [DummyResponseItem(1, "object error", None)]
        )
        with self.assertRaises(PrismeException) as cm:
            send_afgiftsanmeldelse(self.anmeldelse)
        exception = cm.exception
        self.assertEqual(exception.__class__, PrismeException)
        self.assertEqual(exception.code, 1)
        self.assertEqual(exception.message, "object error")

    @override_settings(ENVIRONMENT="production")
    @patch.object(
        PrismeClient,
        "send",
        side_effect=TransportError(message="test", status_code=500),
    )
    def test_send_afgiftsanmeldelse_transport_500(self, mock_client):
        with self.assertRaises(PrismeHttpException) as cm:
            send_afgiftsanmeldelse(self.anmeldelse)
        exception = cm.exception
        self.assertEqual(exception.__class__, PrismeHttpException)
        self.assertEqual(exception.code, 500)
        self.assertEqual(exception.message, "test")

    @override_settings(ENVIRONMENT="production")
    @patch.object(
        PrismeClient,
        "send",
        side_effect=TransportError(message="test", status_code=413),
    )
    def test_send_afgiftsanmeldelse_transport_413(self, mock_client):
        with self.assertRaises(PrismeHttpException) as cm:
            send_afgiftsanmeldelse(self.anmeldelse)
        exception = cm.exception
        self.assertEqual(exception.__class__, PrismeHttpException)
        self.assertEqual(exception.code, 413)
        self.assertEqual(
            exception.message,
            "test\nPrisme-fejl: Afsendelse er for stor (for store filer vedhæftet)",
        )

    @override_settings(ENVIRONMENT="production")
    @patch.object(PrismeClient, "send", side_effect=Fault(message="test", code=123))
    def test_send_afgiftsanmeldelse_zeepfault(self, mock_client):
        with self.assertRaises(PrismeConnectionException) as cm:
            send_afgiftsanmeldelse(self.anmeldelse)
        exception = cm.exception
        self.assertEqual(exception.__class__, PrismeConnectionException)
        self.assertEqual(exception.code, 123)
        self.assertEqual(exception.message, "test")

    @override_settings(ENVIRONMENT="production", PRISME={"wsdl_file": None})
    def test_send_afgiftsanmeldelse_no_wsdl(self):
        with self.assertRaises(PrismeException) as cm:
            send_afgiftsanmeldelse(self.anmeldelse)
        exception = cm.exception
        self.assertEqual(exception.__class__, PrismeException)
        self.assertEqual(exception.code, 0)
        self.assertIn(
            "WSDL ikke konfigureret\nMetode: createCustomDuty\n", exception.message
        )

    @override_settings(
        ENVIRONMENT="production",
        PRISME={"wsdl_file": "https://not-existing-server-for-realz.com/wsdl"},
    )
    def test_client_no_connection(self):
        with self.assertRaises(PrismeConnectionException) as cm:
            _ = PrismeClient().client
        exception = cm.exception
        self.assertIn("Failed connecting to prisme", exception.message)

    @override_settings(
        ENVIRONMENT="production",
        PRISME={
            "wsdl_file": "https://not-existing-server-for-realz.com/wsdl",
            "area": "SULLISSIVIK",
            "proxy": {"socks": "example.com:1234"},
        },
    )
    @override_settings(
        ENVIRONMENT="production",
        PRISME={
            "wsdl_file": "https://not-existing-server-for-realz.com/wsdl",
            "area": "SULLISSIVIK",
        },
    )
    @patch.object(Transport, "load")
    def test_client_wsdl_header(self, mock_load):
        with open(
            os.path.join(os.path.dirname(__file__), "prisme.wsdl"), "rb"
        ) as wsdl_file:
            mock_load.return_value = wsdl_file.read()
        prismeclient = PrismeClient()
        header = prismeclient.create_request_header("createCustomDuty")
        self.assertEqual(header.__class__.__name__, "GWSRequestHeaderDCFUJ")
        self.assertEqual(header.area, "SULLISSIVIK")
        self.assertEqual(header.clientVersion, 1)
        self.assertEqual(header.method, "createCustomDuty")

    @override_settings(
        ENVIRONMENT="production",
        PRISME={
            "wsdl_file": "https://not-existing-server-for-realz.com/wsdl",
            "area": "SULLISSIVIK",
            "proxy": {
                "socks": "example.com:1234",
            },
        },
    )
    @patch.object(Transport, "load")
    def test_client_socks(self, mock_load):
        with open(
            os.path.join(os.path.dirname(__file__), "prisme.wsdl"), "rb"
        ) as wsdl_file:
            mock_load.return_value = wsdl_file.read()
        prismeclient = PrismeClient()
        client = prismeclient.client
        proxy = "socks5://example.com:1234"
        self.assertEqual(
            client.transport.session.proxies, {"http": proxy, "https": proxy}
        )

    @override_settings(
        ENVIRONMENT="production",
        PRISME={
            "wsdl_file": "https://not-existing-server-for-realz.com/wsdl",
            "area": "SULLISSIVIK",
            "auth": {
                "basic": {
                    "username": "test",
                    "domain": "local",
                    "password": "12345",
                }
            },
        },
    )
    @patch.object(Transport, "load")
    def test_client_auth_basic(self, mock_load):
        with open(
            os.path.join(os.path.dirname(__file__), "prisme.wsdl"), "rb"
        ) as wsdl_file:
            mock_load.return_value = wsdl_file.read()
        prismeclient = PrismeClient()
        client = prismeclient.client
        self.assertEqual(
            client.transport.session.auth.__class__.__name__, "HTTPBasicAuth"
        )
        self.assertEqual(client.transport.session.auth.username, "test@local")
        self.assertEqual(client.transport.session.auth.password, "12345")

    @override_settings(
        ENVIRONMENT="production",
        PRISME={
            "wsdl_file": "https://not-existing-server-for-realz.com/wsdl",
            "area": "SULLISSIVIK",
            "auth": {
                "ntlm": {
                    "username": "test",
                    "domain": "local",
                    "password": "12345",
                }
            },
        },
    )
    @patch.object(Transport, "load")
    def test_client_auth_basic(self, mock_load):
        with open(
            os.path.join(os.path.dirname(__file__), "prisme.wsdl"), "rb"
        ) as wsdl_file:
            mock_load.return_value = wsdl_file.read()
        prismeclient = PrismeClient()
        client = prismeclient.client
        self.assertEqual(
            client.transport.session.auth.__class__.__name__, "HttpNtlmAuth"
        )
        self.assertEqual(client.transport.session.auth.username, "local\\test")
        self.assertEqual(client.transport.session.auth.password, "12345")
