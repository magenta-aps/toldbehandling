import base64
from decimal import Decimal
from unittest import TestCase

from django.core.files.base import ContentFile
from django.utils.datetime_safe import date
from lxml import etree

from admin.clients.prisme import CustomDutyRequest

from told_common.data import (  # isort: skip
    Afgiftsanmeldelse,
    Afsender,
    Forsendelsestype,
    FragtForsendelse,
    Modtager,
    Vareafgiftssats,
    Varelinje,
)


class PrismeTest(TestCase):
    def setUp(self) -> None:
        self.anmeldelse = Afgiftsanmeldelse(
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
            ),
            leverandørfaktura_nummer="5678",
            modtager_betaler=False,
            indførselstilladelse="1234",
            betalt=True,
            godkendt=True,
            dato=date(2023, 11, 13),
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

    def test_request_xml(self):
        request = CustomDutyRequest(self.anmeldelse)
        self.maxDiff = None
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
                  <TaxGroupNumber>2</TaxGroupNumber>
                </CustomDutyHeaderLine>
              </CustomDutyHeaderLines>
              <CustomDutyHeaderLines>
                <CustomDutyHeaderLine>
                  <BillAmount>1123.45</BillAmount>
                  <LineAmount>120.00</LineAmount>
                  <LineNum>002</LineNum>
                  <Qty>1</Qty>
                  <TaxGroupNumber>2</TaxGroupNumber>
                </CustomDutyHeaderLine>
              </CustomDutyHeaderLines>
              <CustomsCategory>73A</CustomsCategory>
              <CvrConsignee>12345678</CvrConsignee>
              <CvrConsigner>12345678</CvrConsigner>
              <DeliveryDate>2023-10-01</DeliveryDate>
              <DlvModeId>10</DlvModeId>
              <Duedate>2024-01-01</Duedate>
              <ImportAuthorizationNumber>1234</ImportAuthorizationNumber>
              <LocationCode>None</LocationCode>
              <PaymentParty>1</PaymentParty>
              <TaxNotificationNumber>1</TaxNotificationNumber>
              <Type>TF10</Type>
              <VendInvoiceNumber>5678</VendInvoiceNumber>
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
        self.assertEquals(self.strip_xml_whitespace(request.xml), expected)
