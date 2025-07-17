from unittest.mock import MagicMock, call, patch

from django.test import TestCase

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
