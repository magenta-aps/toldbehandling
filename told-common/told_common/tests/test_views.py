import json
import time
from unittest.mock import MagicMock, Mock, mock_open, patch

from django.contrib.auth.models import User
from django.http import FileResponse, Http404, JsonResponse
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from told_common.views import FileView, RestView


class RestViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.view = RestView()

    def test_patch(self):
        mock_rest_client = Mock()
        mock_response_data = {"id": 1, "name": "Updated Item", "status": "success"}
        mock_rest_client.patch.return_value = mock_response_data

        patch_data = {"name": "Updated Item", "description": "New description"}
        request = self.factory.patch(
            "/api/items/1/",
            data=json.dumps(patch_data),
            content_type="application/json",
        )
        request.user = self.user

        self.view.rest_client = mock_rest_client

        # Call the patch method
        response = self.view.patch(request, path="items/1/")
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 200)

        # Verify rest_client.patch was called with correct arguments
        mock_rest_client.patch.assert_called_once_with("items/1/", patch_data)
        response_data = json.loads(response.content)
        self.assertEqual(response_data, mock_response_data)


class FileViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client = Client()

    # @patch("told_common.rest_client.RestClient")
    @patch("told_common.views.FileView.rest_client")
    def test_get(self, mock_rest_client: MagicMock):
        login_successful = self.client.login(
            username="testuser", password="testpass123"
        )
        self.assertTrue(login_successful)

        # Set timestamp to 5 minutes ago (300 seconds)
        five_minutes_ago = str(time.time() - 300)
        # current_time_string = str(time.time())

        session = self.client.session
        session["user"] = {
            "id": self.user.id,
            "username": self.user.username,
            "email": self.user.email,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "is_superuser": True,
            "groups": [],
            "permissions": [],
        }
        session["access_token"] = "fake_access_token"
        session["refresh_token"] = "fake_refresh_token"
        session["access_token_timestamp"] = five_minutes_ago
        session["refresh_token_timestamp"] = five_minutes_ago
        session.save()

        resp = self.client.get(reverse("leverandørfaktura_view", kwargs={"id": 1}))

        print()
        print(resp)
        print()

    # def test_get_old(self):
    #     """Test the get method with all external dependencies mocked"""
    #     self.view.api = "documents"
    #     self.view.key = "file_path"

    #     mock_rest_client = Mock()
    #     mock_rest_client.get.return_value = {"file_path": "test/file.pdf"}
    #     self.view.rest_client = mock_rest_client

    #     request = self.factory.get("/files/1/")
    #     request.user = self.user

    #     # Mock all external dependencies
    #     with patch("os.path.join", return_value="/media/test/file.pdf"), patch(
    #         "os.path.exists", return_value=True
    #     ), patch(
    #         "builtins.open", mock_open(read_data=b"file content")
    #     ) as mock_file, patch(
    #         "django.conf.settings.MEDIA_ROOT", "/media/"
    #     ):
    #         response = self.view.get(request, id=1)

    #         # Verify the method calls and response
    #         mock_rest_client.get.assert_called_once_with("documents/1")
    #         self.assertIsInstance(response, FileResponse)
    #         mock_file.assert_called_once_with("/media/test/file.pdf", "rb")

    # def test_get_errors(self):
    #     """Test the two places where Http404 is raised"""
    #     self.view.api = "documents"
    #     self.view.key = "file_path"

    #     mock_rest_client = Mock()
    #     self.view.rest_client = mock_rest_client

    #     request = self.factory.get("/files/1/")
    #     request.user = self.user

    #     # Test case 1: Empty file path raises Http404
    #     mock_rest_client.get.return_value = {"file_path": ""}
    #     with self.assertRaises(Http404):
    #         self.view.get(request, id=1)

    #     # Test case 2: File doesn't exist raises Http404
    #     mock_rest_client.get.return_value = {"file_path": "test/file.pdf"}
    #     with patch("os.path.join", return_value="/media/test/file.pdf"), patch(
    #         "os.path.exists", return_value=False
    #     ), patch("django.conf.settings.MEDIA_ROOT", "/media/"):
    #         with self.assertRaises(Http404):
    #             self.view.get(request, id=1)
