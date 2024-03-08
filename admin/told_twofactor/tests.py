from unittest.mock import patch

import requests
from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django_otp.oath import TOTP
from requests import Response
from told_common.rest_client import TotpDeviceRestClient, UserRestClient
from told_common.tests import HasLogin, TestMixin


class TwoFactorSetupViewTest(HasLogin, TestMixin, TestCase):
    url = reverse("twofactor:setup")

    def test_requires_login(self):
        response = self.client.get(self.url, follow=False)
        self.assertEquals(response.status_code, 302)
        self.assertEquals(
            response.headers["Location"], reverse("login") + "?next=" + self.url
        )

    def test_submit_fail(self):
        self.login()
        response = self.client.post(
            self.url,
            {
                "two_factor_setup_view-current_step": "generator",
                "generator-token": "123456",
            },
        )
        self.assertEquals(response.status_code, 200)
        errors = self.get_errors(response.content)
        self.assertEquals(errors, {"generator-token": ["Ugyldig token"]})

    @patch.object(TOTP, "token")
    @patch.object(TotpDeviceRestClient, "create")
    @patch.object(UserRestClient, "this")
    def test_submit_success(self, mock_user_get, mock_create_device, mock_gen_token):
        mock_user_get.side_effect = lambda: None
        mock_create_device.side_effect = lambda x: None
        mock_gen_token.return_value = 112233
        self.login()
        response = self.client.post(
            self.url,
            {
                "two_factor_setup_view-current_step": "generator",
                "generator-token": "112233",
            },
        )
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response.headers["Location"], "/admin")
        sent = mock_create_device.call_args[0][0]
        del sent["key"]
        expected = {
            "user_id": 1,
            "tolerance": 1,
            "t0": 0,
            "step": 30,
            "drift": 1,
            "digits": 6,
            "name": "default",
        }
        self.assertDictEqual(sent, expected)
        self.assertTrue(self.client.session["twofactor_authenticated"])


class TwofactorLoginTest(HasLogin, TestMixin, TestCase):

    def setUp(self):
        self.posted = []

    def mock_requests_post(self, path, status_code):
        print(f"MOCK POST {path} {data} {status_code}")
        expected_prefix = f"{settings.REST_DOMAIN}/api/"
        if path == f"{expected_prefix}/2fa/check":
            self.posted.append(data)
            response = Response()
            response.status_code = status_code
            return response

    def mock_requests_post_accept(self, path, **kwargs):
        return self.mock_requests_post(path, data, headers, 200)

    def mock_requests_post_reject(self, path, **kwargs):
        return self.mock_requests_post(path, data, headers, 401)

    def test_login_missing(self):
        self.client.login()
        response = self.client.post(reverse("twofactor:login"))
        errors = self.get_errors(response.content)
        self.assertEquals(errors, {"twofactor_token": ["Dette felt er påkrævet."]})
        self.assertFalse("twofactor_authenticated" in self.client.session)

    @patch.object(requests, "post")
    def test_login_fail(self, mock_post):
        mock_post.side_effect = self.mock_requests_post_reject
        self.client.login()
        response = self.client.post(reverse("twofactor:login"), {"twofactor_token": "112233"})
        errors = self.get_errors(response.content)
        self.assertEquals(errors, {"twofactor_token": ["Ugyldig token"]})
        self.assertFalse("twofactor_authenticated" in self.client.session)

    @patch.object(requests, "post")
    def test_login_success(self, mock_post):
        mock_post.side_effect = self.mock_requests_post_accept
        self.client.login()
        response = self.client.post(reverse("twofactor:login"), {"twofactor_token": "112233"})
        print(response.status_code)
        print(response.headers)
        print(response.content)
        self.assertTrue("twofactor_authenticated" in self.client.session)
