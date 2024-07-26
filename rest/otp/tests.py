# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from django.test import TestCase
from django.urls import reverse
from otp.api import TOTPDeviceIn
from project.test_mixins import RestMixin
from project.util import json_dump


class TOTPDeviceAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_permissions = []
        cls.user, cls.user_token, cls.user_refresh_token = RestMixin.make_user(
            username="otp-test-user",
            plaintext_password="testpassword1337",
            permissions=cls.user_permissions,
        )

    def test_create(self):
        resp = self.client.post(
            reverse("api-1.0.0:totpdevice_create"),
            TOTPDeviceIn(
                user_id=self.user.id,
                name="test-otp-device",
            ).json(),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 204)
        self.assertEqual(resp.content.decode(), "")
