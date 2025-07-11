from django.core import mail
from django.test import TestCase, override_settings

from admin.utils import send_email


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
