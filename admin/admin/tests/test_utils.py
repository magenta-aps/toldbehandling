from unittest.mock import MagicMock, call, patch

from django.core import mail
from django.test import TestCase, override_settings

from admin.utils import send_email


class UtilsTest(TestCase):
    @patch("admin.utils.render_to_string")
    @patch("admin.utils.EmailMultiAlternatives")
    def test_send_email(
        self, mock_emailMultiAlternatives: MagicMock, mock_render_to_string: MagicMock
    ):
        mock_msg_instance = MagicMock()
        mock_emailMultiAlternatives.return_value = mock_msg_instance

        send_mail_params = {
            "subject": "Test subject",
            "template": "testTemplate.txt",
            "to": ["test@example.com", "test2@example.com"],
        }

        # Test WITHOUT html template
        send_email(**send_mail_params)
        mock_render_to_string.assert_called_once_with("testTemplate.txt", context=None)
        mock_msg_instance.attach_alternative.assert_not_called()
        mock_msg_instance.send.assert_called_once()

        # Test WITH html template
        mock_render_to_string.reset_mock()
        mock_msg_instance.send.reset_mock()

        send_email(**{**send_mail_params, "html_template": "testTemplate.html"})
        mock_render_to_string.assert_has_calls(
            [
                call("testTemplate.txt", context=None),
                call("testTemplate.html", context=None),
            ]
        )
        mock_msg_instance.send.assert_called_once()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SendEmailTest(TestCase):
    def test_afvist_email(self):
        context = {
            "id": 42,
            "status_change_reason": "Dokumentation mangler",
            "afgiftsanmeldelse_link": "https://example.com/anmeldelse/42",
        }

        send_email(
            subject="Din afgiftsanmeldelse er afvist",
            template="admin/emails/afgiftsanmeldelse_afvist.txt",
            html_template="admin/emails/afgiftsanmeldelse_afvist.html",
            to=["modtager@example.com"],
            context=context,
            from_email="noreply@example.com",
        )

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        # Plain text checks
        self.assertIn("42", email.body)
        self.assertIn("Dokumentation mangler", email.body)
        self.assertIn("https://example.com/anmeldelse/42", email.body)

        # HTML part
        html_body, mime = email.alternatives[0]
        self.assertIn("<p>", html_body)
        self.assertIn("42", html_body)
        self.assertIn("Dokumentation mangler", html_body)
        self.assertIn("https://example.com/anmeldelse/42", html_body)
        self.assertEqual(mime, "text/html")
