import base64
from unittest.mock import ANY, MagicMock, call, patch
from uuid import UUID, uuid4

from anmeldelse.models import Afgiftsanmeldelse
from common.api import APIKeyAuth, DjangoPermission, UserOut
from common.eboks import EboksClient, MockResponse
from common.models import EboksBesked, IndberetterProfile
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.files import File
from django.test import TestCase
from django.urls import reverse
from project.test_mixins import RestMixin
from project.util import json_dump
from requests import HTTPError


class CommonTest:
    @classmethod
    def setUpTestData(cls):
        # PERMISSIONS
        cls.view_afgiftsanmeldelse_perm = Permission.objects.get(
            codename="view_afgiftsanmeldelse"
        )

        # User-1 (CVR)
        cls.user, cls.user_token, cls.user_refresh_token = RestMixin.make_user(
            username="payment-test-user",
            plaintext_password="testpassword1337",
            permissions=[cls.view_afgiftsanmeldelse_perm],
        )

        cls.indberetter = IndberetterProfile.objects.create(
            user=cls.user,
            cvr="13371337",
            api_key=uuid4(),
        )

        # User-2 (CPR)
        cls.auth_read_apikeys = Permission.objects.create(
            name="Kan læse API-nøgler",
            codename="read_apikeys",
            content_type=ContentType.objects.get_for_model(
                User, for_concrete_model=False
            ),
        )

        cls.user2, cls.user2_token, cls.user2_refresh_token = RestMixin.make_user(
            username="payment-test-user2",
            plaintext_password="testpassword1337",
            permissions=[cls.view_afgiftsanmeldelse_perm, cls.auth_read_apikeys],
        )

        cls.indberetter2 = IndberetterProfile.objects.create(
            user=cls.user2,
            cpr="1234567890",
            api_key=uuid4(),
        )


class CommonModelsTests(TestCase):
    def test_eboks_besked_content(self):
        db_model = EboksBesked()
        self.assertEqual(db_model.content, None)

        db_model = EboksBesked(
            titel="Test",
            cvr=1234567890,
            pdf=b"test-pdf-body",
        )
        self.assertEqual(
            db_model.content,
            (
                b"<?xml version='1.0' encoding='UTF-8'?>\n<Dispatch xmlns=\"urn:eboks:"
                b'en:3.0.0"><DispatchRecipient><Id>1234567890</Id><Type>V</Type><Nati'
                b"onality>DK</Nationality></DispatchRecipient><ContentTypeId></Content"
                b"TypeId><Title>Test</Title><Content><Data>dGVzdC1wZGYtYm9keQ==</Data>"
                b"<FileExtension>pdf</FileExtension></Content></Dispatch>"
            ),
        )

        db_model = EboksBesked(
            titel="Test",
            cpr=1122334455,
            pdf=b"test-pdf-body",
        )

        self.assertEqual(
            db_model.content,
            (
                b"<?xml version='1.0' encoding='UTF-8'?>\n<Dispatch xmlns=\"urn:eboks:en:3"
                b'.0.0"><DispatchRecipient><Id>1122334455</Id><Type>P</Type><Nationality>'
                b"DK</Nationality></DispatchRecipient><ContentTypeId></ContentTypeId><Titl"
                b"e>Test</Title><Content><Data>dGVzdC1wZGYtYm9keQ==</Data><FileExtension>p"
                b"df</FileExtension></Content></Dispatch>"
            ),
        )


class CommonAPITests(CommonTest, TestCase):
    def test_APIKeyAuth_authenticate(self):
        mock_request = MagicMock()
        resp = APIKeyAuth().authenticate(mock_request, self.indberetter.api_key)
        self.assertEqual(resp, self.user)
        self.assertEqual(mock_request.user, self.user)

    def test_DjangoPermission_has_permission(self):
        anmeldelse_perm_content_type = ContentType.objects.get_for_model(
            Afgiftsanmeldelse
        )

        permission = DjangoPermission(
            (
                f"{anmeldelse_perm_content_type.app_label}."
                f"{self.view_afgiftsanmeldelse_perm.codename}"
            )
        )
        self.assertEqual(
            permission.has_permission(MagicMock(user=self.user), MagicMock()), True
        )

    @patch("common.api.User.indberetter_data")
    def test_UserOut_resolve_indberetter_data_has_attr(
        self, mock_indberetter_data: MagicMock
    ):
        self.assertEqual(
            UserOut.resolve_indberetter_data(self.user), mock_indberetter_data
        )


class CommonUserAPITests(CommonTest, TestCase):
    def test_get_user(self):
        resp = self.client.get(
            reverse("api-1.0.0:user_view"),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            {
                "id": self.user.id,
                "username": "payment-test-user",
                "first_name": "",
                "last_name": "",
                "email": "",
                "is_superuser": False,
                "groups": [],
                "permissions": ["anmeldelse.view_afgiftsanmeldelse"],
                "indberetter_data": {"cpr": None, "cvr": 13371337},
                "twofactor_enabled": False,
            },
        )

    def test_get_user_cpr(self):
        resp = self.client.get(
            reverse("api-1.0.0:user_cpr_get", args=[self.indberetter2.cpr]),
            HTTP_AUTHORIZATION=f"Bearer {self.user2_token}",
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            {
                "id": self.user2.id,
                "username": "payment-test-user2",
                "first_name": "",
                "last_name": "",
                "email": "",
                "is_superuser": False,
                "groups": [],
                "permissions": [
                    "anmeldelse.view_afgiftsanmeldelse",
                    "auth.read_apikeys",
                ],
                "indberetter_data": {"cpr": 1234567890, "cvr": None},
                "access_token": ANY,
                "refresh_token": ANY,
            },
        )

    def test_get_user_cpr_apikey(self):
        resp = self.client.get(
            reverse("api-1.0.0:user_cpr_get_apikey", args=[self.indberetter2.cpr]),
            HTTP_AUTHORIZATION=f"Bearer {self.user2_token}",
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            {"api_key": str(self.user2.indberetter_data.api_key)},
        )

    def test_create_user(self):
        resp = self.client.post(
            reverse("api-1.0.0:user_create"),
            data=json_dump(
                {
                    "username": "test-user3",
                    "password": "testpassword1337",
                    "first_name": "Test",
                    "last_name": "User",
                    "email": "testuser3@magenta-aps.dk",
                    "indberetter_data": {"cpr": 1122334455},
                }
            ),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 200)
        resp_json = resp.json()
        self.assertTrue(isinstance(resp_json["id"], int))
        self.assertEqual(
            resp_json,
            {
                "id": ANY,
                "username": "test-user3",
                "first_name": "Test",
                "last_name": "User",
                "email": "testuser3@magenta-aps.dk",
                "is_superuser": False,
                "groups": [],
                "permissions": [],
                "indberetter_data": {"cpr": 1122334455, "cvr": None},
                "access_token": ANY,
                "refresh_token": ANY,
            },
        )

    def test_create_user_exceptions(self):
        test_user = {
            "username": "test-user3",
            "password": "testpassword1337",
            "first_name": "Test",
            "last_name": "User",
            "email": "testuser3@magenta-aps.dk",
        }

        resp = self.client.post(
            reverse("api-1.0.0:user_create"),
            data=json_dump({**test_user, "groups": ["test-group"]}),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 422)
        self.assertEqual(
            resp.json(),
            {"detail": "Group does not exist"},
        )

        resp = self.client.post(
            reverse("api-1.0.0:user_create"),
            data=json_dump(test_user),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 422)
        self.assertEqual(
            resp.json(),
            {"detail": "indberetter_data does not exist"},
        )

    def test_list(self):
        resp = self.client.get(
            reverse("api-1.0.0:user_list"),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            {
                "count": 2,
                "items": [
                    {
                        "id": self.user.id,
                        "username": "payment-test-user",
                        "first_name": "",
                        "last_name": "",
                        "email": "",
                        "is_superuser": False,
                        "groups": [],
                        "permissions": ["anmeldelse.view_afgiftsanmeldelse"],
                        "indberetter_data": {"cpr": None, "cvr": 13371337},
                        "twofactor_enabled": False,
                    },
                    {
                        "id": self.user2.id,
                        "username": "payment-test-user2",
                        "first_name": "",
                        "last_name": "",
                        "email": "",
                        "is_superuser": False,
                        "groups": [],
                        "permissions": [
                            "anmeldelse.view_afgiftsanmeldelse",
                            "auth.read_apikeys",
                        ],
                        "indberetter_data": {"cpr": 1234567890, "cvr": None},
                        "twofactor_enabled": False,
                    },
                ],
            },
        )

    def test_update(self):
        resp = self.client.patch(
            reverse("api-1.0.0:user_update", args=[self.indberetter2.cpr]),
            data=json_dump(
                {
                    # NOTE: required by the payload, but not used in the handler
                    "username": self.user2.username,
                    "first_name": "Test",
                    "last_name": "User",
                    "email": self.user2.email,
                    "indberetter_data": {"cvr": 1337133700},
                }
            ),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            {
                "id": self.user2.id,
                "username": "payment-test-user2",
                "first_name": "Test",
                "last_name": "User",
                "email": "",
                "is_superuser": False,
                "groups": [],
                "permissions": [
                    "anmeldelse.view_afgiftsanmeldelse",
                    "auth.read_apikeys",
                ],
                "indberetter_data": {"cpr": 1234567890, "cvr": 1337133700},
                "access_token": ANY,
                "refresh_token": ANY,
            },
        )

    def test_update_exceptions(self):
        resp = self.client.patch(
            reverse("api-1.0.0:user_update", args=[self.indberetter2.cpr]),
            data=json_dump(
                {
                    # NOTE: required by the payload, but not used in the handler
                    "username": self.user2.username,
                    "first_name": "Test",
                    "last_name": "User",
                    "email": self.user2.email,
                    "groups": ["test-group"],
                }
            ),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 422)
        self.assertEqual(
            resp.json(),
            {"detail": "Group does not exist"},
        )


class CommonEboksBeskedAPITests(CommonTest, TestCase):
    def test_create_eboksbesked(self):
        resp = self.client.post(
            reverse("api-1.0.0:eboksbesked_create"),
            data=json_dump(
                {
                    "titel": "test-besked",
                    "cpr": 1234567890,
                    "pdf": str(base64.b64encode(b"test-pdf-body")),
                }
            ),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"id": ANY})


class CommonEboksModuleTests(CommonTest, TestCase):
    def _eboks_client(self, mock=False):
        return EboksClient(
            mock=mock,
            client_certificate="test-cert",
            client_private_key="test-key",
            verify="test-verify",
            client_id="test-client-id",
            system_id="test-system-id",
            host="http://test-host",
            timeout=30,
        )

    def test_mock_response(self):
        msg_id = 1234567890
        mock_response = MockResponse(msg_id)
        self.assertEqual(
            mock_response.json(),
            {
                "message_id": msg_id,
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
            },
        )

    @patch("common.eboks.requests.session")
    def test_eboks_client_get_client_info(self, mock_requests_session: MagicMock):
        mock_request_resp = MagicMock(raise_for_status=MagicMock())
        mock_request = MagicMock(return_value=mock_request_resp)
        mock_requests_session.return_value = MagicMock(
            request=mock_request,
        )

        eboks_client = self._eboks_client()
        resp = eboks_client.get_client_info()

        mock_requests_session.assert_called_once()
        mock_request.assert_called_once_with(
            "GET",
            f"{eboks_client.host}/rest/client/{eboks_client.client_id}/",
            None,
            None,
            timeout=eboks_client.timeout,
        )
        mock_request_resp.raise_for_status.assert_called_once()

        self.assertEqual(resp, mock_request_resp)

    @patch("common.eboks.requests.session")
    def test_eboks_client_get_recipient_status(self, mock_requests_session: MagicMock):
        mock_request_resp = MagicMock(raise_for_status=MagicMock())
        mock_request = MagicMock(return_value=mock_request_resp)
        mock_requests_session.return_value = MagicMock(
            request=mock_request,
        )

        eboks_client = self._eboks_client()
        resp = eboks_client.get_recipient_status(
            ["test-msg-id-1", "test-msg-id-2"], retries=3, retry_wait_time=10
        )

        mock_requests_session.assert_called_once()
        mock_request.assert_called_once_with(
            "GET",
            f"{eboks_client.host}/rest/messages/{eboks_client.client_id}/",
            {"message_id": ["test-msg-id-1", "test-msg-id-2"]},
            None,
            timeout=eboks_client.timeout,
        )

        mock_requests_session.assert_called_once()
        self.assertEqual(resp, mock_request_resp)

    @patch("common.eboks.sleep")
    @patch("common.eboks.requests.session")
    def test_eboks_client_get_recipient_status_http_error(
        self, mock_requests_session: MagicMock, mock_sleep: MagicMock
    ):
        mock_request_resp = MagicMock(
            raise_for_status=MagicMock(side_effect=HTTPError("test-http_error"))
        )
        mock_request = MagicMock(return_value=mock_request_resp)
        mock_requests_session.return_value = MagicMock(
            request=mock_request,
        )

        eboks_client = self._eboks_client()
        with self.assertRaises(HTTPError):
            _ = eboks_client.get_recipient_status(
                ["test-msg-id-1", "test-msg-id-2"], retry_wait_time=1
            )

        mock_requests_session.assert_called_once()
        mock_request.assert_called_with(
            "GET",
            f"{eboks_client.host}/rest/messages/{eboks_client.client_id}/",
            {"message_id": ["test-msg-id-1", "test-msg-id-2"]},
            None,
            timeout=eboks_client.timeout,
        )

        # Assert the sleep calls, which veries the number of times a retry was attempted
        mock_sleep.assert_has_calls([call(1), call(2), call(4), call(8)])

    @patch("common.eboks.uuid4")
    def test_get_message_id(self, mock_uuid4: MagicMock):
        mock_uuid = uuid4().hex
        mock_uuid4.return_value = MagicMock(hex=mock_uuid)

        eboks_client = self._eboks_client()
        resp = eboks_client.get_message_id()

        self.assertEqual(
            resp,
            "{sys_id}{client_id}{uuid}".format(
                sys_id=eboks_client.system_id.zfill(6),
                client_id=eboks_client.client_id,
                uuid=mock_uuid,
            ),
        )

    @patch("common.eboks.uuid4")
    def test_get_message_id_mock_client(self, mock_uuid4: MagicMock):
        mock_uuid = uuid4().hex
        mock_uuid4.return_value = MagicMock(hex=mock_uuid)

        eboks_client = self._eboks_client(mock=True)
        resp = eboks_client.get_message_id()
        self.assertEqual(resp, mock_uuid)

    @patch("common.eboks.uuid4")
    @patch("common.eboks.requests.session")
    def test_send_message(
        self, mock_requests_session: MagicMock, mock_uuid4: MagicMock
    ):
        # Mocking
        mock_uuid = uuid4().hex
        mock_uuid4.return_value = MagicMock(hex=mock_uuid)

        mock_request_resp = MagicMock(status_code=200, raise_for_status=MagicMock())
        mock_request = MagicMock(return_value=mock_request_resp)
        mock_requests_session.return_value = MagicMock(
            request=mock_request,
        )

        # Test data
        eboks_client = self._eboks_client()
        msg_id = "{sys_id}{client_id}{uuid}".format(
            sys_id=eboks_client.system_id.zfill(6),
            client_id=eboks_client.client_id,
            uuid=mock_uuid,
        )

        msg = EboksBesked.objects.create(
            titel="Test",
            cvr=1234567890,
            pdf=b"test-pdf-body",
        )

        # Invoke & Assert
        _ = eboks_client.send_message(msg)

        mock_requests_session.assert_called_once()
        mock_request_resp.raise_for_status.assert_called_once()
        mock_request.assert_called_once_with(
            "PUT",
            f"{eboks_client.url_with_prefix}3/dispatchsystem/{eboks_client.system_id}/dispatches/{msg_id}",
            None,
            msg.content,
            timeout=eboks_client.timeout,
        )

    @patch("common.eboks.uuid4")
    def test_send_message_mock(self, mock_uuid4: MagicMock):
        mock_uuid4.return_value = MagicMock(hex=uuid4().hex)

        eboks_client = self._eboks_client(mock=True)
        resp = eboks_client.send_message(EboksBesked())
        self.assertEqual(
            resp.json(),
            {
                "message_id": mock_uuid4.return_value.hex,
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
            },
        )

    @patch("common.eboks.uuid4")
    @patch("common.eboks.requests.session")
    def test_send_message_http_error(
        self, mock_requests_session: MagicMock, mock_uuid4: MagicMock
    ):
        mock_uuid4.return_value = MagicMock(hex=uuid4().hex)

        mock_request_resp = MagicMock(
            status_code=200,
            raise_for_status=MagicMock(
                side_effect=HTTPError(
                    response=MagicMock(status_code=409, content="test-http-error")
                )
            ),
        )
        mock_request = MagicMock(return_value=mock_request_resp)
        mock_requests_session.return_value = MagicMock(
            request=mock_request,
        )

        msg = EboksBesked.objects.create(
            titel="Test",
            cvr=1234567890,
            pdf=b"test-pdf-body",
        )

        # Invoke & Assert
        eboks_client = self._eboks_client()
        msg_id = "{sys_id}{client_id}{uuid}".format(
            sys_id=eboks_client.system_id.zfill(6),
            client_id=eboks_client.client_id,
            uuid=mock_uuid4.return_value.hex,
        )

        with self.assertRaises(HTTPError):
            _ = eboks_client.send_message(msg, retry_wait_time=1)

        mock_requests_session.assert_called_once()
        mock_request.assert_called_with(
            "PUT",
            f"{eboks_client.url_with_prefix}3/dispatchsystem/{eboks_client.system_id}/dispatches/{msg_id}",
            None,
            msg.content,
            timeout=eboks_client.timeout,
        )

    def test_parse_exception(self):
        resp = self._eboks_client().parse_exception(
            HTTPError(
                response=MagicMock(
                    status_code=409,
                    text="test-text-error",
                    json=MagicMock(side_effect=ValueError("test-json-error")),
                )
            )
        )

        self.assertEqual(
            resp,
            {
                "status_code": 409,
                "error": "test-text-error",
            },
        )

        # cover AttributeError / when there is no status_code
        resp_no_status_code = self._eboks_client().parse_exception(
            HTTPError("test-text-error", response=CustomHTTPErrorResponseMock())
        )

        self.assertEqual(
            resp_no_status_code,
            {
                "error": "test-text-error",
            },
        )

    def test_from_settings(self):
        eboks_client = EboksClient.from_settings()
        self.assertEqual(
            eboks_client.__dict__,
            {
                "_mock": True,
            },
        )

        with patch("common.eboks.settings") as mock_settings:
            mock_settings.EBOKS = {
                "mock": False,
                "content_type_id": "",
            }
            eboks_client = EboksClient.from_settings()
            self.assertEqual(
                eboks_client.__dict__,
                {
                    "_mock": False,
                    "client_id": None,
                    "system_id": "None",
                    "host": None,
                    "timeout": 60,
                    "session": ANY,
                    "url_with_prefix": "/int/rest/srv.svc/",
                },
            )
