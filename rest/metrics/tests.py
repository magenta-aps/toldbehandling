# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from project.test_mixins import RestMixin


class MetricsTest:
    @classmethod
    def setUpTestData(cls):
        cls.user_permissions = [
            Permission.objects.get(codename="view_payment"),
            Permission.objects.get(codename="add_payment"),
            Permission.objects.get(codename="change_payment"),
            Permission.objects.get(codename="delete_payment"),
        ]

        cls.user, cls.user_token, cls.user_refresh_token = RestMixin.make_user(
            username="payment-test-user",
            plaintext_password="testpassword1337",
            permissions=cls.user_permissions,
        )
        cls.user.user_permissions.add(
            Permission.objects.get(codename="view_privatafgiftsanmeldelse"),
        )


class MetricsAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_permissions = []
        cls.user, cls.user_token, cls.user_refresh_token = RestMixin.make_user(
            username="metrics-test-user",
            plaintext_password="testpassword1337",
            permissions=cls.user_permissions,
        )

    def test_health_storage(self):
        resp = self.client.get(
            reverse("api-1.0.0:metrics_health_storage"),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content.decode(), "OK")

    @patch("metrics.api.tempfile.NamedTemporaryFile")
    def test_health_storage_error(self, mock_named_temporary_file):
        mock_named_temporary_file.side_effect = Exception("Test")

        resp = self.client.get(
            reverse("api-1.0.0:metrics_health_storage"),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.content.decode(), "ERROR")

    def test_health_database(self):
        resp = self.client.get(
            reverse("api-1.0.0:metrics_health_database"),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content.decode(), "OK")

    @patch("metrics.api.connection.ensure_connection")
    def test_health_database_error(self, mock_ensure_connection):
        mock_ensure_connection.side_effect = Exception("Test")

        resp = self.client.get(
            reverse("api-1.0.0:metrics_health_database"),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.content.decode(), "ERROR")

    @patch("payment.provider_handlers.requests.get")
    def test_health_payment_providers(self, mock_requests_get):
        mock_requests_get.return_value.status_code = 405
        resp = self.client.get(
            reverse("api-1.0.0:metrics_health_payment_providers"),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content.decode(), "OK")

    @patch("metrics.api.get_provider_handler")
    def test_health_payment_providers_error(self, mock_get_provider_handler):
        mock_get_provider_handler.side_effect = Exception("Test")

        resp = self.client.get(
            reverse("api-1.0.0:metrics_health_payment_providers"),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.content.decode(), "ERROR")
