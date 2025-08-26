from unittest.mock import MagicMock, patch
from urllib.parse import quote_plus

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from told_common.view_mixins import LoginRequiredMixin, PermissionsRequiredMixin


class LoginRequiredMixinNeedsLoginTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.mixin = LoginRequiredMixin()

    @override_settings(LOGIN_PROVIDER_CLASS="dummy")
    def test_needs_login_redirects_to_saml_login_if_no_saml_data(self):
        request = self.factory.get("/protected/")
        request.session = {}
        response = self.mixin.needs_login(request)
        self.assertEqual(response.status_code, 302)
        expected_url = reverse("login:login") + "?back=" + quote_plus("/protected/")
        self.assertEqual(response.url, expected_url)

    @override_settings(LOGIN_PROVIDER_CLASS="dummy", LOGIN_SESSION_DATA_KEY="saml")
    @patch("told_common.view_mixins.RestClient.login_saml_user")
    @patch("told_common.view_mixins.RestTokenUserMiddleware.set_user")
    def test_needs_login_with_saml_data_logs_in_user(
        self, mock_set_user, mock_login_saml_user
    ):
        request = self.factory.get("/protected/")
        request.session = {"saml": {"some": "data"}}

        # Mock RestClient.login_saml_user -> (user, token)
        mock_user = MagicMock()
        mock_token = MagicMock()
        mock_login_saml_user.return_value = (mock_user, mock_token)

        response = self.mixin.needs_login(request)

        # Should not redirect
        self.assertIsNone(response)
        # User should be stored in session
        self.assertEqual(request.session["user"], mock_user)
        # Token.save() should be called with request
        mock_token.save.assert_called_once_with(request, save_refresh_token=True)
        # Middleware set_user should be called
        mock_set_user.assert_called_once_with(request)


class PermissionsRequiredMixinTests(TestCase):
    def test_has_permissions_raises_without_userdata_or_request(self):
        # Calling has_permissions without userdata or request should raise
        with self.assertRaisesMessage(
            Exception, "Must specify either userdata or request"
        ):
            PermissionsRequiredMixin.has_permissions()
