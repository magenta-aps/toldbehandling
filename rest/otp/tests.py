# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from unittest.mock import ANY, MagicMock

from django.test import TestCase
from django.urls import reverse
from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice
from otp.api import TOTPDeviceIn
from otp.auth import AuthenticationBackend
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
                name="test-otp-create-device",
            ).json(),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 204)
        self.assertEqual(resp.content.decode(), "")

    def test_list(self):
        TOTPDevice.objects.create(
            user_id=self.user.id,
            name="test-otp-list-devices",
        )

        resp = self.client.get(
            reverse("api-1.0.0:totpdevice_list"),
            {"user": self.user.id},
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            [
                {
                    "key": ANY,
                    "tolerance": 1,
                    "t0": 0,
                    "step": 30,
                    "drift": 0,
                    "digits": 6,
                    "name": "test-otp-list-devices",
                    "confirmed": True,
                    "user_id": self.user.id,
                }
            ],
        )

    def test_check(self):
        totp_device = TOTPDevice.objects.create(
            user=self.user,
            name="test-otp-check-2fa",
        )

        # Generate a valid OTP token
        totp = TOTP(key=totp_device.bin_key, step=totp_device.step, t0=totp_device.t0)
        valid_token = totp.token()

        resp = self.client.post(
            reverse("api-1.0.0:twofactor_check"),
            content_type="application/json",
            data=json_dump(
                {
                    "user_id": self.user.id,
                    "twofactor_token": valid_token,
                }
            ),
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), True)

    def test_check_error(self):
        resp = self.client.post(
            reverse("api-1.0.0:twofactor_check"),
            content_type="application/json",
            data=json_dump(
                {
                    "user_id": self.user.id,
                    "twofactor_token": "1234",
                }
            ),
        )

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json(), {"detail": "Token invalid"})


class AuthenticationBackendTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mock_request = MagicMock()
        cls.user_pwd = "testpassword1337"
        cls.user_permissions = []
        cls.user, cls.user_token, cls.user_refresh_token = RestMixin.make_user(
            username="otp-test-user-auth",
            plaintext_password=cls.user_pwd,
            permissions=cls.user_permissions,
        )

    def test_authenticate(self):
        totp_device = TOTPDevice.objects.create(
            user=self.user,
            name="test-otp-check-2fa",
        )
        totp = TOTP(key=totp_device.bin_key, step=totp_device.step, t0=totp_device.t0)
        valid_token = totp.token()

        self.assertEqual(
            self.user,
            AuthenticationBackend().authenticate(
                self.mock_request,
                self.user.username,
                self.user_pwd,
                twofactor_token=valid_token,
            ),
        )

    def test_authenticate_no_2fa_token(self):
        self.assertEqual(
            None,
            AuthenticationBackend().authenticate(
                self.mock_request,
                self.user.username,
                self.user_pwd,
            ),
        )
