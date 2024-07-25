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

    def test_health_database(self):
        resp = self.client.get(
            reverse("api-1.0.0:metrics_health_database"),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content.decode(), "OK")

    @patch("payment.provider_handlers.requests.get")
    def test_health_payment_providers(self, mock_requests_get):
        mock_requests_get.return_value.status_code = 405
        resp = self.client.get(
            reverse("api-1.0.0:metrics_health_payment_providers"),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content.decode(), "OK")
