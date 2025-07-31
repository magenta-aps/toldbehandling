import json
from unittest.mock import Mock

from django.contrib.auth.models import User
from django.http import JsonResponse
from django.test import RequestFactory, TestCase
from told_common.views import RestView


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
