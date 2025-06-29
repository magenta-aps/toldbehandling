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
from told_common.data import Afgiftsanmeldelse, Forsendelsestype, Vareafgiftssats
from told_common.util import get_file_base64
from xmltodict import parse as xml_to_dict
from zeep.exceptions import TransportError
from zeep.transports import Transport

logger = logging.getLogger(__name__)


class PrismeException(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message


class PrismeHttpException(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message


class PrismeConnectionException(Exception):
    def __init__(
        self,
        message,
        code: Optional[int] = None,
        inner_exception: Optional[Exception] = None,
    ):
        self.message = message
        self.code = code
        self.inner_exception = inner_exception


class PrismeRequestObject:
    @property
    def method(self):
        raise NotImplementedError  # pragma: no cover

    @property
    def xml(self):
        raise NotImplementedError  # pragma: no cover

    @property
    def reply_class(self):
        raise NotImplementedError  # pragma: no cover


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
        if self.afgiftsanmeldelse.fragtforsendelse:
            forsendelsestype = self.afgiftsanmeldelse.fragtforsendelse.forsendelsestype
            if forsendelsestype == Forsendelsestype.FLY:
                return 40  # FLY
            if forsendelsestype == Forsendelsestype.SKIB:
                return 10  # SKIB
        # return 90  # Egen kraft
        raise ValueError("Missing fragtforsendelse or postforsendelse")

    @property
    def forsendelse(self):
        return (
            self.afgiftsanmeldelse.fragtforsendelse
            or self.afgiftsanmeldelse.postforsendelse
        )

    @property
    def stedkode(self):
        stedkode = self.afgiftsanmeldelse.modtager.stedkode
        if stedkode is not None:
            return str(stedkode).zfill(3)
        return ""

    @property
    def betaler(self):
        if self.afgiftsanmeldelse.betales_af == "modtager":
            return "Consignee"
        return "Consigner"

    @property
    def forsendelsesnummer(self):
        if self.afgiftsanmeldelse.fragtforsendelse:
            return self.afgiftsanmeldelse.fragtforsendelse.fragtbrevsnummer
        if self.afgiftsanmeldelse.postforsendelse:
            return self.afgiftsanmeldelse.postforsendelse.postforsendelsesnummer
        raise ValueError("Missing fragtforsendelse or postforsendelse")

    @property
    def forbindelsesnummer(self):
        if self.afgiftsanmeldelse.fragtforsendelse:
            return self.afgiftsanmeldelse.fragtforsendelse.forbindelsesnr
        return "999"

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

    @staticmethod
    def empty_if_none(value):
        if value is None:
            return ""
        return value

    @property
    def xml(self):
        data = {
            "Type": "TF10",
            "CvrConsignee": self.empty_if_none(self.afgiftsanmeldelse.modtager.cvr),
            "CvrConsigner": self.empty_if_none(self.afgiftsanmeldelse.afsender.cvr),
            "TaxNotificationNumber": self.afgiftsanmeldelse.id,
            "BillOfLadingOrPostalNumber": self.forsendelsesnummer,
            "ConnectionNumber": self.empty_if_none(self.forbindelsesnummer),
            "CustomsCategory": self.toldkategori,
            "LocationCode": self.empty_if_none(self.stedkode),
            "PaymentParty": self.betaler,
            "DlvModeId": self.leveringsmåde,
            "DeliveryDate": self.forsendelse.afgangsdato.isoformat(),
            "ImportAuthorizationNumber": self.empty_if_none(
                self.afgiftsanmeldelse.indførselstilladelse
            ),
            "VendInvoiceNumber": self.empty_if_none(
                self.afgiftsanmeldelse.leverandørfaktura_nummer
            ),
            "WebDueDate": self.afgiftsanmeldelse.beregnet_faktureringsdato.isoformat(),
            "CustomDutyHeaderLines": [
                {
                    "CustomDutyHeaderLine": {
                        "LineNum": str(i).zfill(3),
                        "TaxGroupNumber": str(
                            varelinje.vareafgiftssats.afgiftsgruppenummer
                        ).zfill(3),
                        "Qty": self.qty(varelinje),
                        "BillAmount": str(varelinje.fakturabeløb or ""),
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
        if (
            self.afgiftsanmeldelse.fragtforsendelse
            and self.afgiftsanmeldelse.fragtforsendelse.fragtbrev
        ):
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
                raise PrismeConnectionException(
                    f"Failed connecting to prisme: {e}", inner_exception=e
                )
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
        xml_list: list = [xml] if type(xml) is not list else xml
        container_class = self.client.get_type("tns:ArrayOfGWSRequestXMLDCFUJ")
        return container_class(list([item_class(xml=x) for x in xml_list]))

    def send(
        self, request_object: PrismeRequestObject
    ) -> Optional[List[PrismeResponseObject]]:
        try:
            if not self.settings["wsdl_file"]:
                raise PrismeException(
                    0,
                    "\n".join(
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


def prisme_send_dummy(
    request_object: PrismeRequestObject,
) -> Optional[List[PrismeResponseObject]]:
    """Dummy implementation of PrismeClient.send for development purposes

    OBS: This implementation is based on how we mocked in test. This has now
    been moved to this function instead as well, so it's only specified in one place.
    """
    if settings.PRISME_MOCK_HTTP_ERROR == 413:  # type: ignore
        raise TransportError("Server returned HTTP status 413", 413)

    return [
        CustomDutyResponse(
            request_object,
            """
                <CustomDutyTableFUJ>
                <RecId>5637147578</RecId>
                <TaxNotificationNumber>44668899</TaxNotificationNumber>
                <DeliveryDate>2023-04-07T00:00:00</DeliveryDate>
                </CustomDutyTableFUJ>
            """,
        )
    ]


def send_afgiftsanmeldelse(
    afgiftsanmeldelse: Afgiftsanmeldelse,
) -> Optional[List[CustomDutyResponse | PrismeResponseObject]]:
    try:
        request = CustomDutyRequest(afgiftsanmeldelse)
        if settings.ENVIRONMENT != "production":  # type: ignore
            return prisme_send_dummy(request)
        return PrismeClient().send(request)
    except TransportError as e:
        message = [e.message]
        if e.status_code == 413:
            message.append(
                "Prisme-fejl: Afsendelse er for stor (for store filer vedhæftet)"
            )
        raise PrismeHttpException(e.status_code, "\n".join(message))
    except zeep.exceptions.Fault as e:
        raise PrismeConnectionException(e.message, e.code, e)
