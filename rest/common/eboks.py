import urllib
import urllib.parse
from dataclasses import dataclass
from time import sleep
from uuid import uuid4

import requests
from common.models import EboksBesked, EboksDispatch
from django.conf import settings
from requests.exceptions import HTTPError


@dataclass()
class MockResponse:
    status_code: int = 200

    def __init__(self, message_id):
        self._message_id = message_id

    def json(self):
        return {
            "message_id": self._message_id,
            "recipients": [
                {
                    "nr": "",
                    "recipient_type": "cpr",
                    "nationality": "Denmark",
                    "status": "",
                    "reject_reason": "",
                    "post_processing_status": "",
                }
            ],
        }


class EboksClient(object):
    def __init__(
        self,
        mock=False,
        client_certificate=None,
        client_private_key=None,
        verify=None,
        client_id=None,
        system_id=None,
        host=None,
        timeout=60,
    ):
        self._mock = mock
        if not self._mock:
            self.client_id = client_id
            self.system_id = str(system_id)
            self.host = host
            self.timeout = timeout
            self.session = requests.session()
            self.session.cert = (client_certificate, client_private_key)
            self.session.verify = verify
            self.session.headers.update({"content-type": "application/xml"})
            self.url_with_prefix = urllib.parse.urljoin(self.host, "/int/rest/srv.svc/")

    def _make_request(self, url, method="GET", params=None, data=None):
        r = self.session.request(method, url, params, data, timeout=self.timeout)
        r.raise_for_status()
        return r

    def get_client_info(self):
        url = urllib.parse.urljoin(
            self.host, "/rest/client/{client_id}/".format(client_id=self.client_id)
        )
        return self._make_request(url=url)

    def get_recipient_status(self, message_ids, retries=0, retry_wait_time=10):
        url = urllib.parse.urljoin(
            self.host, "/rest/messages/{client_id}/".format(client_id=self.client_id)
        )
        try:
            return self._make_request(url=url, params={"message_id": message_ids})
        except HTTPError:
            if retries <= 3:
                sleep(retry_wait_time)  # wait 10, 20 then 40 seconds
                return self.get_recipient_status(
                    message_ids, retries + 1, retry_wait_time * 2
                )
            else:
                raise

    def get_message_id(self):
        if self._mock:
            return uuid4().hex
        return "{sys_id}{client_id}{uuid}".format(
            sys_id=self.system_id.zfill(6), client_id=self.client_id, uuid=uuid4().hex
        )

    def send_message(
        self, besked: EboksBesked, message_id=None, retries=3, retry_wait_time=10
    ):
        if message_id is None:
            message_id = self.get_message_id()  # Generate random
        if self._mock:
            return MockResponse(message_id)
        url = urllib.parse.urljoin(
            self.url_with_prefix,
            f"3/dispatchsystem/{self.system_id}/dispatches/{message_id}",
        )
        dispatch = EboksDispatch.objects.get_or_create(
            message_id=message_id,
            defaults={
                "besked": besked,
            },
        )
        besked.forsøg += 1

        try:
            response = self._make_request(url=url, method="PUT", data=besked.content)
            besked.sendt = True
            besked.save(update_fields=("sendt", "forsøg"))
            dispatch.status_code = response.status_code
            dispatch.save(update_fields=("status_code",))
            return response

        except HTTPError as e:
            if hasattr(e, "response"):
                dispatch.status_code = e.response.status_code
            besked.save(update_fields=("forsøg",))
            dispatch.save(update_fields=("status_code",))

            if retries > 0:
                if hasattr(e, "response"):
                    if e.response.status_code == 409:
                        # message_id allerede brugt
                        message_id = None
                sleep(retry_wait_time)  # 10, 20, 40 sekunder
                return self.send_message(  # Rekursivt kald. Prøv med en ny Dispatch
                    besked, message_id, retries - 1, retry_wait_time * 2
                )
            else:
                print(
                    f"Failed sending message (id={besked.id}, message_id={message_id})"
                )
                raise

    @staticmethod
    def parse_exception(e):
        """
        parse Request exception and return a error dict
        :param e:
        :return: error dictionary
        """
        error = {"error": str(e)}
        try:
            status_code = e.response.status_code
            try:
                error = {"status_code": status_code, "error": e.response.json()}
            except ValueError:
                error = {"status_code": status_code, "error": e.response.text}
        except AttributeError:
            pass
        return error

    def close(self):
        if hasattr(self, "_session"):
            self.session.close()

    @classmethod
    def from_settings(cls):
        eboks_settings = dict(settings.EBOKS)
        eboks_settings.pop("content_type_id")
        return cls(**eboks_settings)
