from unittest.mock import ANY, MagicMock, patch
from uuid import uuid4

from anmeldelse.models import Afgiftsanmeldelse
from common.api import APIKeyAuth, DjangoPermission, UserOut
from common.models import EboksBesked, IndberetterProfile
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from project.test_mixins import RestMixin


class CommonTest:
    @classmethod
    def setUpTestData(cls):
        # User-1 (CVR)
        cls.view_afgiftsanmeldelse_perm = Permission.objects.get(
            codename="view_afgiftsanmeldelse"
        )

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
