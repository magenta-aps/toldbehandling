from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from project.test_mixins import RestMixin


class MetricsTest(TestCase):
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


class MetricsAPITest(MetricsTest):
    def test_get_all(self):
        resp = self.client.get(
            reverse("api-1.0.0:metrics_get_all"),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp["Content-Type"], "text/plain; version=0.0.4; charset=utf-8"
        )
        self.assertGreater(len(resp.content), 0)
