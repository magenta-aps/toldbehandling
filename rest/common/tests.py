from unittest.mock import MagicMock
from uuid import uuid4

from anmeldelse.models import Afgiftsanmeldelse
from common.api import APIKeyAuth, DjangoPermission
from common.models import EboksBesked, IndberetterProfile
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from project.test_mixins import RestMixin


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


class CommonAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
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
