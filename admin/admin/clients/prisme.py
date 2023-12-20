import logging
from datetime import date, datetime
from os.path import basename
from typing import List, Optional, Union

import zeep
from dict2xml import dict2xml as dict_to_xml
from django.conf import settings
from requests import Session
from requests.auth import HTTPBasicAuth
from requests_ntlm import HttpNtlmAuth
from told_common.util import get_file_base64
from xmltodict import parse as xml_to_dict
from zeep.transports import Transport

from told_common.data import (  # isort: skip
    Afgiftsanmeldelse,
    Forsendelsestype,
    Vareafgiftssats,
)

logger = logging.getLogger(__name__)


class PrismeException(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message


class PrismeRequestObject:
    @property
    def method(self):
        raise NotImplementedError

    @property
    def xml(self):
        raise NotImplementedError

    @property
    def reply_class(self):
        raise NotImplementedError

    @staticmethod
    def prepare(value, is_amount=False):
        if value is None:
            return ""
        if is_amount:
            value = f"{value:.2f}"
        if isinstance(value, datetime):
            value = f"{value:%Y-%m-%dT%H:%M:%S}"
        if isinstance(value, date):
            value = f"{value:%Y-%m-%d}"
        return value


class PrismeResponseObject(object):
    def __init__(self, request, xml):
        self.request = request
        self.xml = xml


class CustomDutyRequest(PrismeRequestObject):
    def __init__(
        self,
        afgiftsanmeldelse: Afgiftsanmeldelse,
    ):
        self.afgiftsanmeldelse = afgiftsanmeldelse

    method = "createCustomDuty"

    @property
    def reply_class(self):
        return CustomDutyResponse

    @property
    def leveringsmåde(self):
        if self.afgiftsanmeldelse.postforsendelse:
            return 50  # POST
        forsendelsestype = self.afgiftsanmeldelse.fragtforsendelse.forsendelsestype
        if forsendelsestype == Forsendelsestype.FLY:
            return 40  # FLY
        if forsendelsestype == Forsendelsestype.SKIB:
            return 10  # SKIB
        # return 90  # Egen kraft

    @property
    def forsendelse(self):
        return (
            self.afgiftsanmeldelse.fragtforsendelse
            or self.afgiftsanmeldelse.postforsendelse
        )

    @property
    def afsenderbykode(self):
        if self.afgiftsanmeldelse.postforsendelse:
            return self.afgiftsanmeldelse.postforsendelse.afsenderbykode
        return ""

    @property
    def betaler(self):
        if self.afgiftsanmeldelse.modtager_betaler:
            return "Consignee"
        return "Consigner"

    @property
    def forsendelsesnummer(self):
        if self.afgiftsanmeldelse.fragtforsendelse:
            return self.afgiftsanmeldelse.fragtforsendelse.fragtbrevsnummer
        if self.afgiftsanmeldelse.postforsendelse:
            return self.afgiftsanmeldelse.postforsendelse.postforsendelsesnummer
        return ""

    @property
    def forbindelsesnummer(self):
        if self.afgiftsanmeldelse.fragtforsendelse:
            return self.afgiftsanmeldelse.fragtforsendelse.forbindelsesnr
        return ""

    @property
    def toldkategori(self):
        return self.afgiftsanmeldelse.toldkategori

    def qty(self, varelinje):
        if varelinje.vareafgiftssats.enhed in (
            Vareafgiftssats.Enhed.LITER,
            Vareafgiftssats.Enhed.KILOGRAM,
        ):
            return varelinje.mængde
        else:
            return varelinje.antal

    @property
    def xml(self):
        data = {
            "Type": "TF10",
            "CvrConsignee": self.afgiftsanmeldelse.afsender.cvr,
            "CvrConsigner": self.afgiftsanmeldelse.modtager.cvr,
            "TaxNotificationNumber": self.afgiftsanmeldelse.id,
            "BillOfLadingOrPostalNumber": self.forsendelsesnummer,
            "ConnectionNumber": self.forbindelsesnummer,
            "CustomsCategory": self.toldkategori,
            "LocationCode": self.afsenderbykode,
            "PaymentParty": self.betaler,
            "DlvModeId": self.leveringsmåde,
            "DeliveryDate": self.forsendelse.afgangsdato.isoformat(),
            "ImportAuthorizationNumber": self.afgiftsanmeldelse.indførselstilladelse,
            "VendInvoiceNumber": self.afgiftsanmeldelse.leverandørfaktura_nummer,
            "WebDueDate": self.afgiftsanmeldelse.beregnet_faktureringsdato.isoformat(),
            "CustomDutyHeaderLines": [
                {
                    "CustomDutyHeaderLine": {
                        "LineNum": str(i).zfill(3),
                        "TaxGroupNumber": str(
                            varelinje.vareafgiftssats.afgiftsgruppenummer
                        ).zfill(3),
                        "Qty": self.qty(varelinje),
                        "BillAmount": str(varelinje.fakturabeløb),
                        "LineAmount": str(varelinje.afgiftsbeløb),
                    }
                }
                for i, varelinje in enumerate(self.afgiftsanmeldelse.varelinjer, 1)
            ],
            "files": {
                "file": [
                    {
                        "Name": basename(self.afgiftsanmeldelse.leverandørfaktura.name),
                        "Content": get_file_base64(
                            self.afgiftsanmeldelse.leverandørfaktura
                        ),
                    }
                ]
            },
        }
        if self.afgiftsanmeldelse.fragtforsendelse:
            data["files"]["file"].append(
                {
                    "Name": basename(
                        self.afgiftsanmeldelse.fragtforsendelse.fragtbrev.name
                    ),
                    "Content": get_file_base64(
                        self.afgiftsanmeldelse.fragtforsendelse.fragtbrev
                    ),
                }
            )

        return dict_to_xml(data, wrap="CustomDutyHeader")


class CustomDutyResponse(PrismeResponseObject):
    def __init__(self, request, xml):
        super().__init__(request, xml)
        data = xml_to_dict(xml)["CustomDutyTableFUJ"]
        self.record_id = data["RecId"]
        self.tax_notification_number = data["TaxNotificationNumber"]
        self.delivery_date = data["DeliveryDate"]


class PrismeClient:
    def __init__(self):
        self._client = None
        self.settings = settings.PRISME

    @property
    def client(self):
        if self._client is None:
            wsdl = self.settings["wsdl_file"]
            session = Session()
            if "proxy" in self.settings:
                if "socks" in self.settings["proxy"]:
                    proxy = f'socks5://{self.settings["proxy"]["socks"]}'
                    session.proxies = {"http": proxy, "https": proxy}

            auth_settings = self.settings.get("auth")
            if auth_settings:
                if "basic" in auth_settings:
                    basic_settings = auth_settings["basic"]
                    session.auth = HTTPBasicAuth(
                        f'{basic_settings["username"]}@{basic_settings["domain"]}',
                        basic_settings["password"],
                    )
                elif "ntlm" in auth_settings:
                    ntlm_settings = auth_settings["ntlm"]
                    session.auth = HttpNtlmAuth(
                        f"{ntlm_settings['domain']}\\{ntlm_settings['username']}",
                        ntlm_settings["password"],
                    )
            try:
                self._client = zeep.Client(
                    wsdl=wsdl,
                    transport=Transport(
                        session=session, timeout=3600, operation_timeout=3600
                    ),
                    # settings=Settings(raw_response=True)
                )
            except Exception as e:
                raise Exception(f"Failed connecting to prisme: {e}")
            self._client.set_ns_prefix(
                "tns", "http://schemas.datacontract.org/2004/07/Dynamics.Ax.Application"
            )
        return self._client

    def create_request_header(self, method, area=None, client_version=1):
        request_header_class = self.client.get_type("tns:GWSRequestHeaderDCFUJ")
        if area is None:
            area = self.settings["area"]
        return request_header_class(
            clientVersion=client_version, area=area, method=method
        )

    def create_request_body(self, xml: Union[str, List[str]]):
        item_class = self.client.get_type("tns:GWSRequestXMLDCFUJ")
        if type(xml) is not list:
            xml = [xml]
        container_class = self.client.get_type("tns:ArrayOfGWSRequestXMLDCFUJ")
        return container_class(list([item_class(xml=x) for x in xml]))

    def send(
        self, request_object: PrismeRequestObject
    ) -> Optional[List[PrismeResponseObject]]:
        try:
            if not self.settings["wsdl_file"]:
                raise PrismeException(
                    0,
                    "\n\n".join(
                        [
                            "WSDL ikke konfigureret",
                            f"Metode: {request_object.method}",
                            f"XML: {request_object.xml}",
                        ]
                    ),
                )

            outputs = []

            request_class = self.client.get_type("tns:GWSRequestDCFUJ")
            request = request_class(
                requestHeader=self.create_request_header(request_object.method),
                xmlCollection=[self.create_request_body(request_object.xml)],
            )
            # reply is of type GWSReplyDCFUJ
            reply = self.client.service.processService(request)

            # reply.status is of type GWSReplyStatusDCFUJ
            if reply.status.replyCode != 0:
                raise PrismeException(reply.status.replyCode, reply.status.replyText)

            # reply_item is of type GWSReplyInstanceDCFUJ
            for reply_item in reply.instanceCollection.GWSReplyInstanceDCFUJ:
                if reply_item.replyCode == 0:
                    logger.info(
                        "Receiving from %s:\n%s", request_object.method, reply_item.xml
                    )
                    outputs.append(
                        request_object.reply_class(request_object, reply_item.xml)
                    )
                else:
                    raise PrismeException(reply_item.replyCode, reply_item.replyText)
            return outputs
        except PrismeException as e:
            logger.info(
                "Error in process_service for %s: %s", request_object.method, str(e)
            )
            raise e


def send_afgiftsanmeldelse(
    afgiftsanmeldelse: Afgiftsanmeldelse,
) -> List[CustomDutyResponse]:
    return PrismeClient().send(CustomDutyRequest(afgiftsanmeldelse))
