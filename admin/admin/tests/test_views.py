# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from requests import HTTPError, Response
from told_common.data import Afsender, Modtager, Toldkategori
from told_common.tests.tests import HasLogin


class BaseTest(HasLogin, TestCase):

    def setUp(self):
        self.rest_client_patcher = patch("told_common.view_mixins.RestClient")
        self.rest_client_mock = MagicMock()

        self.rest_client_class_mock = self.rest_client_patcher.start()
        self.rest_client_class_mock.return_value = self.rest_client_mock

        self.addCleanup(self.rest_client_patcher.stop)
        cache.clear()


class TF10Test(BaseTest):

    def setUp(self):
        super().setUp()
        self.indberetter_data = {"cpr": "0101011234", "cvr": "123456"}

        def get_item(key):
            return {"id": 111, "fragtforsendelse": {"id": 222}}.get(key, None)

        def get_indberetter(k=None):
            if k is None:
                return MagicMock(get=lambda k: {"cvr": "12345678"}[k])
            elif k == "indberetter_data":
                return self.indberetter_data

        self.indberetter_mock = MagicMock()
        self.indberetter_mock.__bool__.return_value = True
        self.indberetter_mock.get.side_effect = get_indberetter

        self.item_mock = MagicMock()
        self.item_mock.status = "kladde"
        self.item_mock.__getitem__.side_effect = get_item
        self.item_mock.afsender = MagicMock(Afsender)
        self.item_mock.afsender.cvr = 1111

        self.item_mock.modtager = MagicMock(Modtager)
        self.item_mock.modtager.id = 1
        self.item_mock.modtager.cvr = None
        self.item_mock.indberetter = self.indberetter_mock
        self.item_mock.toldkategori = "73A"
        self.item_mock.kategori = "73A"
        self.item_mock.kræver_cvr = True
        self.item_mock.betales_af = "afsender"

        self.item_mock.oprettet_af = {"email": "jack@sparrow.sp"}

        self.rest_client_mock.afgiftanmeldelse.get.return_value = self.item_mock

        kategori = Toldkategori(kategori="73A", navn="foo", kræver_cvr=True)
        self.rest_client_mock.toldkategori.list.return_value = [kategori]

        self.prisme_data = {
            "send_til_prisme": True,
            "modtager_stedkode": "001",
            "toldkategori": "73A",
        }
        self.email_data = {
            "send_til_prisme": False,
            "modtager_stedkode": "001",
            "toldkategori": "73A",
            "status": "afvist",
            "notat1": "foo",
        }
        self.url = reverse("tf10_view", kwargs={"id": 1})

    def test_send_to_prisme(self):
        self.login()
        self.client.post(self.url, data=self.prisme_data)
        self.rest_client_mock.prismeresponse.create.assert_called_once()

    def test_send_to_prisme_permission_denied(self):
        self.login(
            userdata_extra={
                "permissions": [
                    "auth.admin",
                    "aktør.view_afsender",
                    "aktør.view_modtager",
                    "sats.view_vareafgiftssats",
                    # "anmeldelse.prisme_afgiftsanmeldelse",
                    "aktør.change_modtager",
                    "forsendelse.view_postforsendelse",
                    "forsendelse.view_fragtforsendelse",
                    "anmeldelse.view_afgiftsanmeldelse",
                    "anmeldelse.view_varelinje",
                    "anmeldelse.change_afgiftsanmeldelse",
                ],
                "is_superuser": False,
            }
        )
        response = self.client.post(self.url, data=self.prisme_data)
        self.rest_client_mock.prismeresponse.create.assert_not_called()
        self.assertEqual(response.status_code, 403)

    def test_send_to_prisme_no_cvr(self):
        self.login()
        self.assertEqual(self.item_mock.modtager.cvr, None)
        self.item_mock.betales_af = "modtager"
        self.client.post(self.url, data=self.prisme_data)
        self.rest_client_mock.prismeresponse.create.assert_not_called()

    @patch("admin.views.log")
    def test_prismeresponse_create_error(self, mock_log):
        self.rest_client_mock.prismeresponse.create.side_effect = ValueError
        self.login()

        self.client.post(self.url, data=self.prisme_data)
        mock_log.error.assert_called()
        self.assertIn("sendt til prisme, men fejlede", mock_log.error.call_args[0][0])

    @patch("admin.views.send_afgiftsanmeldelse")
    @patch("admin.views.log")
    def test_send_afgiftsanmeldelse_no_responses(
        self, mock_log, mock_send_afgiftsanmeldelse
    ):
        self.login()
        mock_send_afgiftsanmeldelse.return_value = []
        self.client.post(self.url, data=self.prisme_data)
        mock_log.error.assert_called()

        self.assertIn("fik ikke noget svar", mock_log.error.call_args[0][0])

    @override_settings(EMAIL_NOTIFICATIONS_ENABLED=True)
    @patch("admin.views.send_email")
    def test_reject_and_send_mail(self, mock_send_email):
        self.login()
        self.client.post(self.url, data=self.email_data)
        self.rest_client_mock.prismeresponse.create.assert_not_called()
        mock_send_email.assert_called_once()

    @patch("admin.views.send_email")
    def test_reject_and_no_notat(self, mock_send_email):
        self.login()
        self.client.post(
            self.url,
            data={
                "send_til_prisme": False,
                "modtager_stedkode": "001",
                "toldkategori": "73A",
                "status": "afvist",
            },
        )
        self.rest_client_mock.prismeresponse.create.assert_not_called()
        mock_send_email.assert_not_called()

    def test_reject_and_no_status(self):
        self.login()
        self.client.post(
            self.url,
            data={
                "send_til_prisme": False,
                "modtager_stedkode": "001",
                "toldkategori": "73A",
                "notat1": "foo",
            },
        )
        self.rest_client_mock.notat.create.assert_called_once()

    def test_reject_and_not_afvist(self):
        self.login()
        self.client.post(
            self.url,
            data={
                "send_til_prisme": False,
                "modtager_stedkode": "001",
                "toldkategori": "73A",
                "status": "ny",
                "notat1": "foo",
            },
        )
        self.rest_client_mock.afgiftanmeldelse.set_status.assert_called_once()

    def test_reject_and_permission_denied(self):
        self.login(
            userdata_extra={
                "permissions": [
                    "auth.admin",
                    "aktør.view_afsender",
                    "aktør.view_modtager",
                    "sats.view_vareafgiftssats",
                    "anmeldelse.prisme_afgiftsanmeldelse",
                    "aktør.change_modtager",
                    "forsendelse.view_postforsendelse",
                    "forsendelse.view_fragtforsendelse",
                    "anmeldelse.view_afgiftsanmeldelse",
                    "anmeldelse.view_varelinje",
                    # "anmeldelse.change_afgiftsanmeldelse",
                ],
                "is_superuser": False,
            }
        )
        response = self.client.post(
            self.url,
            data={
                "send_til_prisme": False,
                "modtager_stedkode": "001",
                "toldkategori": "73A",
                "status": "afvist",
                "notat1": "foo",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_send_to_prisme_http_500_error(self):
        self.login()

        response = Response()
        response.status_code = 500

        self.rest_client_mock.afgiftanmeldelse.set_status.side_effect = HTTPError(
            response=response
        )

        self.client.post(self.url, data=self.email_data)
        self.rest_client_mock.prismeresponse.create.assert_not_called()

    def test_send_to_prisme_http_404_error(self):
        self.login()

        response = Response()
        response.status_code = 404

        self.rest_client_mock.afgiftanmeldelse.set_status.side_effect = HTTPError(
            response=response
        )

        self.client.post(self.url, data=self.email_data)
        self.rest_client_mock.prismeresponse.create.assert_not_called()
