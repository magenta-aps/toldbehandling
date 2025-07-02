# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
import os
from datetime import date
from io import BytesIO
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.http import FileResponse
from django.test import TestCase
from django.urls import reverse
from requests import HTTPError, Response
from told_common.data import Afsender, Modtager
from told_common.tests.tests import HasLogin
from weasyprint import HTML

User = get_user_model()


class IndexViewTest(HasLogin, TestCase):

    def test_redirect_with_cvr(self):
        self.login(userdata={"indberetter_data": {"cvr": "12345678"}})

        response = self.client.get("/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("tf10_list"))

    def test_redirect_without_cvr(self):
        self.login(userdata=None)

        response = self.client.get("/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("tf5_list"))


class BaseTest(HasLogin, TestCase):

    def setUp(self):
        self.rest_client_patcher = patch("told_common.view_mixins.RestClient")
        self.rest_client_mock = MagicMock()

        self.rest_client_class_mock = self.rest_client_patcher.start()
        self.rest_client_class_mock.return_value = self.rest_client_mock


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

        self.item_mock = MagicMock()
        self.item_mock.status = "kladde"
        self.item_mock.__getitem__.side_effect = get_item
        self.item_mock.afsender = MagicMock(Afsender)
        self.item_mock.modtager = MagicMock(Modtager)

        self.indberetter_mock = MagicMock()
        self.indberetter_mock.__bool__.return_value = True
        self.indberetter_mock.get.side_effect = get_indberetter

        self.item_mock.indberetter = self.indberetter_mock

        self.rest_client_mock.afgiftanmeldelse.get.return_value = self.item_mock

    def test_update_tf10_as_speditør(self):
        self.login(userdata_extra={"indberetter_data": self.indberetter_data})
        response = self.client.get(reverse("tf10_edit", kwargs={"id": 1}))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(hasattr(response.context["form"], "speditører"))

    def test_view_tf10(self):
        self.login()
        response = self.client.post(reverse("tf10_view", kwargs={"id": 1}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.rest_client_mock.afgiftanmeldelse.set_status.assert_called_once()


class TF5Test(BaseTest):

    def setUp(self):
        super().setUp()

        def get_item(key):
            return {"id": 111}.get(key, None)

        with open("/tmp/test_faktura.txt", "w") as f:
            f.write("foo")

        # Create a PDF from HTML
        html = HTML(string="<p>Leverandørfaktura</p>")
        pdf_buffer = BytesIO()
        html.write_pdf(target=pdf_buffer)
        pdf_buffer.seek(0)  # Rewind the buffer

        # If .open() is used in a context manager
        open_pdf_mock = MagicMock()
        open_pdf_mock.__enter__.return_value = pdf_buffer
        open_pdf_mock.__exit__.return_value = None

        self.privat_anmeldelse_item_mock = MagicMock()
        self.privat_anmeldelse_item_mock.indleveringsdato = date(2020, 1, 1)
        self.privat_anmeldelse_item_mock.oprettet = date(2020, 1, 1)
        self.privat_anmeldelse_item_mock.id = 1
        self.privat_anmeldelse_item_mock.status = "ny"
        self.privat_anmeldelse_item_mock.leverandørfaktura_nummer = 1
        self.privat_anmeldelse_item_mock.__getitem__.side_effect = get_item
        self.privat_anmeldelse_item_mock.payment_status = "paid"
        self.privat_anmeldelse_item_mock.leverandørfaktura.open.return_value = (
            open_pdf_mock
        )

        self.rest_client_mock.privat_afgiftsanmeldelse.list.return_value = (
            1,
            [self.privat_anmeldelse_item_mock],
        )

        self.rest_client_mock.privat_afgiftsanmeldelse.get.return_value = (
            self.privat_anmeldelse_item_mock
        )

        self.payment_mock = MagicMock()
        self.payment_mock.id = 123
        self.get_payment_item_mock = MagicMock()
        self.get_payment_item_mock.__getitem__.side_effect = get_item
        self.payment_mock.__getitem__.return_value = self.get_payment_item_mock

        self.rest_client_mock.payment.create.return_value = self.payment_mock
        self.rest_client_mock.payment.get_by_declaration.return_value = (
            self.payment_mock
        )

        self.rest_client_mock.payment.refresh.return_value = True

    def test_list_view(self):
        self.login()
        response = self.client.get(reverse("tf5_list"))
        context = response.context

        self.assertEqual(response.status_code, 200)
        self.assertEqual(context["title"], "Mine indførselstilladelser")
        self.assertTrue(context["can_create"])

    def test_tf5_view(self):
        self.login()
        response = self.client.get(reverse("tf5_view", kwargs={"id": 1}))
        context = response.context

        self.assertEqual(response.status_code, 200)
        self.assertTrue(context["can_view_tilladelse"])
        self.assertTrue(context["can_send_tilladelse"])

    def test_tf5_permission_view(self):
        self.login()
        data = {"opret": True, "send": True}
        url = reverse("tf5_tilladelse", kwargs={"id": 1})
        response = self.client.post(url, data=data)

        self.assertEqual(response.status_code, 302)
        self.assertIn("1.pdf", os.listdir("/tf5"))
        self.rest_client_mock.eboks.create.assert_called_once()

    def test_tf5_permission_view_permission_denied(self):
        self.login(
            userdata_extra={
                "permissions": ["anmeldelse.view_privatafgiftsanmeldelse"],
                "is_superuser": False,
            }
        )
        data = {"opret": True, "send": True}
        url = reverse("tf5_tilladelse", kwargs={"id": 1})
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 403)

    def test_tf5_permission_view_not_paid(self):
        self.login()
        data = {"opret": True, "send": True}
        url = reverse("tf5_tilladelse", kwargs={"id": 1})
        self.privat_anmeldelse_item_mock.payment_status = "not_paid"
        response = self.client.post(url, data=data)

        self.assertEqual(response.status_code, 403)

    def test_tf5_permission_item_does_not_exist(self):
        self.login()
        data = {"opret": True, "send": True}
        url = reverse("tf5_tilladelse", kwargs={"id": 1})

        response = Response()
        response.status_code = 404

        self.rest_client_mock.privat_afgiftsanmeldelse.get.side_effect = HTTPError(
            response=response
        )
        response = self.client.post(url, data=data)

        self.assertEqual(response.status_code, 404)

    def test_tf5_permission_unknown_error(self):
        self.login()
        data = {"opret": True, "send": True}
        url = reverse("tf5_tilladelse", kwargs={"id": 1})

        response = Response()
        response.status_code = 500

        self.rest_client_mock.privat_afgiftsanmeldelse.get.side_effect = HTTPError(
            response=response
        )
        with self.assertRaises(HTTPError):
            self.client.post(url, data=data)

    def test_tf5_permission_view_get_file(self):
        self.login()
        data = {"opret": True, "send": True}
        url = reverse("tf5_tilladelse", kwargs={"id": 1})
        self.client.post(url, data=data)

        response = self.client.get(url, data=data)
        self.assertIsInstance(response, FileResponse)

    def test_tf5_payment_checkout_view(self):
        self.login()
        url = reverse("tf5_payment_checkout", kwargs={"id": 1})
        response = self.client.get(url)
        context = response.context
        self.assertEqual(response.status_code, 200)
        self.assertEqual(context["payment"].id, 123)

    def test_tf5_payment_checkout_view_payment_not_found(self):
        self.login()
        url = reverse("tf5_payment_checkout", kwargs={"id": 1})
        self.rest_client_mock.payment.create.return_value = None

        with self.assertRaises(Exception) as cm:
            self.client.get(url)

        self.assertEqual(str(cm.exception), "Betaling kunne ikke findes eller oprettes")

    def test_tf5_payment_details_view(self):
        self.login()

        url = reverse("tf5_payment_details", kwargs={"id": 1})
        response = self.client.get(url)
        context = response.context
        self.assertEqual(response.status_code, 200)
        self.assertEqual(context["payment"].id, 123)

    def test_tf5_payment_details_view_payment_not_found(self):
        self.login()

        url = reverse("tf5_payment_details", kwargs={"id": 1})
        self.rest_client_mock.payment.get_by_declaration.return_value = None

        with self.assertRaises(ObjectDoesNotExist) as cm:
            self.client.get(url)
        self.assertEqual(str(cm.exception), "Betaling kunne ikke findes")

    def test_tf5_payment_refresh_view(self):
        self.login()
        url = reverse("tf5_payment_refresh", kwargs={"id": 1})
        response = self.client.post(url)

        self.assertEqual(response.json()["payment_refreshed"], True)
