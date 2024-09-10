# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from unittest.mock import MagicMock, patch

from aktør.models import Afsender, Modtager, Speditør
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from project.test_mixins import RestMixin, RestTestMixin
from project.util import json_dump


class AfsenderTest(RestTestMixin, TestCase):
    __test__ = True
    object_class = Afsender

    def setUp(self) -> None:
        super().setUp()
        self.creation_data = self.afsender_data
        self.calculated_fields = {
            "stedkode": None,
        }

    def create_items(self):
        self.precreated_item = self.afsender

    invalid_itemdata = {
        "cvr": ["a", 123456789, -1],
        "postnummer": ["a", -1, 0, 999, 10000],
    }
    valid_itemdata = {
        "navn": "Testfirma 3",
        "adresse": "Testvej 42b",
        "postnummer": 4321,
        "by": "TestBy2",
        "postbox": "456",
        "telefon": "654321",
        "cvr": 12345670,
    }
    unique_fields = []
    exclude_fields = ["postnummer_ref", "eksplicit_stedkode"]

    # Expected object in the database as dict
    @property
    def expected_object_data(self):
        return {"id": self.afsender.id, **self.creation_data}

    @property
    def update_object_data(self):
        if not hasattr(self, "_update_object_data"):
            self._update_object_data = {
                key: value
                for key, value in self.expected_object_data.items()
                if value is not None
            }
            self._update_object_data.update(
                {
                    "adresse": "Testvej 50",
                    "postnummer": 5678,
                    "by": "TestMetropol",
                    "postbox": "123567",
                    "telefon": "112",
                    "cvr": 11111111,
                }
            )
        return self._update_object_data

    def test_str(self):
        self.assertEqual(
            str(self.afsender),
            f"Afsender(navn={self.afsender_data['navn']}, cvr={self.afsender_data['cvr']})",
        )


class ModtagerTest(RestTestMixin, TestCase):
    __test__ = True
    plural_classname = "modtagere"
    object_class = Modtager

    def setUp(self) -> None:
        super().setUp()
        self.creation_data = self.modtager_data
        self.calculated_fields = {
            "stedkode": None,
        }

    def create_items(self):
        self.precreated_item = self.modtager

    invalid_itemdata = {
        "cvr": ["a", 123456789, -1],
        "postnummer": ["a", -1, 0, 999, 10000],
    }
    unique_fields = []
    valid_itemdata = {
        "navn": "Testfirma 3",
        "adresse": "Testvej 42b",
        "postnummer": 4321,
        "by": "TestBy2",
        "postbox": "456",
        "telefon": "654321",
        "cvr": 12345670,
        "kreditordning": False,
    }
    exclude_fields = ["postnummer_ref", "eksplicit_stedkode"]

    # Expected object in the database as dict
    @property
    def expected_object_data(self):
        return {"id": self.modtager.id, **self.creation_data}

    @property
    def update_object_data(self):
        if not hasattr(self, "_update_object_data"):
            self._update_object_data = {
                key: value
                for key, value in self.expected_object_data.items()
                if value is not None
            }
            self._update_object_data.update(
                {
                    "adresse": "Testvej 50",
                    "postnummer": 5678,
                    "by": "TestMetropol",
                    "postbox": "123567",
                    "telefon": "112",
                    "cvr": 11111111,
                }
            )
        return self._update_object_data

    def test_str(self):
        self.assertEqual(
            str(self.modtager),
            f"Modtager(navn={self.modtager_data['navn']}, cvr={self.modtager_data['cvr']})",
        )


class AfsenderAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.add_afsender_perm = Permission.objects.get(codename="add_afsender")
        cls.add_modtager_perm = Permission.objects.get(codename="add_modtager")

        cls.user, cls.user_token, cls.user_refresh_token = RestMixin.make_user(
            username="aktoer-test-user",
            plaintext_password="testpassword1337",
            permissions=[
                cls.add_afsender_perm,
                cls.add_modtager_perm,
            ],
        )

    def test_create_afsender_error(self):
        resp = self.client.post(
            reverse("api-1.0.0:afsender_create"),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
            data=json_dump(
                {
                    "payload": {
                        "navn": None,
                        "adresse": None,
                        "postnummer": None,
                        "by": None,
                        "postbox": None,
                        "telefon": None,
                        "cvr": None,
                        "kladde": None,
                    }
                }
            ),
        )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json(),
            {
                "__all__": [
                    "Begrænsning “aktuel_afsender_har_navn” er overtrådt.",
                    "Begrænsning “aktuel_afsender_har_adresse” er overtrådt.",
                    "Begrænsning “aktuel_afsender_har_postnummer” er overtrådt.",
                    "Begrænsning “aktuel_afsender_har_by” er overtrådt.",
                ]
            },
        )

    def test_create_modtager_error(self):
        resp = self.client.post(
            reverse("api-1.0.0:modtager_create"),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
            data=json_dump(
                {
                    "payload": {
                        "navn": None,
                        "adresse": None,
                        "postnummer": None,
                        "by": None,
                        "postbox": None,
                        "telefon": None,
                        "cvr": None,
                        "kreditordning": None,
                        "kladde": None,
                    }
                }
            ),
        )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json(),
            {
                "__all__": [
                    "Begrænsning “aktuel_modtager_har_navn” er overtrådt.",
                    "Begrænsning “aktuel_modtager_har_adresse” er overtrådt.",
                    "Begrænsning “aktuel_modtager_har_postnummer” er overtrådt.",
                    "Begrænsning “aktuel_modtager_har_by” er overtrådt.",
                ]
            },
        )


class SpeditørAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.view_speeditoer = Permission.objects.get(codename="view_speditør")

        cls.user, cls.user_token, cls.user_refresh_token = RestMixin.make_user(
            username="aktoer-speeditør-test-user",
            plaintext_password="testpassword1337",
            permissions=[cls.view_speeditoer],
        )

        # Create some test data
        cls.speeditoer = Speditør.objects.create(
            cvr=10001337,
            navn="speeditoer1337",
        )

    def test_list(self):
        resp = self.client.get(
            reverse("api-1.0.0:speditør_list"),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            {"count": 1, "items": [{"cvr": 10001337, "navn": "speeditoer1337"}]},
        )
