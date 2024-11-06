# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from unittest.mock import MagicMock, patch

from aktør.models import Afsender, Aktør, Modtager, Speditør
from common.models import Postnummer
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from project.test_mixins import RestMixin, RestTestMixin
from project.util import json_dump


class AktoerTest(TestCase):
    def test_aktoer_model_save_postnr_ref_exists_postnr_does_not(self):
        new_postnr_model = Postnummer(
            postnummer=8000,
            navn="Aarhus C",
            dage=0,
            stedkode=1,
        )

        # We use the "Afsender" model, since "Aktør" is an abstraction-model
        new_model = Afsender(
            navn=None,
            adresse=None,
            postnummer=None,
            postnummer_ref=new_postnr_model,
            eksplicit_stedkode=None,
            by=None,
            postbox=None,
            telefon=None,
            cvr=None,
            kladde=True,
        )

        new_model.save()

        self.assertIsNone(new_model.postnummer_ref)

    def test_aktoer_model_stedkode_property(self):
        new_postnr_model = Postnummer(
            postnummer=8000,
            navn="Aarhus C",
            dage=0,
            stedkode=1,
        )

        new_model = Afsender(
            navn=None,
            adresse=None,
            postnummer=None,
            postnummer_ref=new_postnr_model,
            eksplicit_stedkode="lorem ipsum",
            by=None,
            postbox=None,
            telefon=None,
            cvr=None,
            kladde=True,
        )

        self.assertEqual(new_model.stedkode, "lorem ipsum")

        new_model.eksplicit_stedkode = None
        self.assertEqual(new_model.stedkode, new_postnr_model.stedkode)

    def test_aktoer_model_stedkode_property_setter(self):
        new_postnr_model = Postnummer(
            postnummer=8000,
            navn="Aarhus C",
            dage=0,
            stedkode=1,
        )

        new_model = Afsender(
            navn=None,
            adresse=None,
            postnummer=None,
            postnummer_ref=new_postnr_model,
            eksplicit_stedkode="lorem ipsum",
            by=None,
            postbox=None,
            telefon=None,
            cvr=None,
            kladde=True,
        )

        new_model.stedkode = 1
        self.assertIsNone(new_model.eksplicit_stedkode)


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
    exclude_fields = ["postnummer_ref", "eksplicit_stedkode", "land"]

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
    exclude_fields = ["postnummer_ref", "eksplicit_stedkode", "land"]

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


class SpeditørTest(TestCase):
    def test_speditoer_to_string(self):
        new_model = Speditør(cvr=13371337, navn="En 1337 speditoer")
        self.assertEqual(str(new_model), f"Speditør(En 1337 speditoer)")


class SpeditørAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.view_speditoer = Permission.objects.get(codename="view_speditør")

        cls.user, cls.user_token, cls.user_refresh_token = RestMixin.make_user(
            username="aktoer-speditoer-test-user",
            plaintext_password="testpassword1337",
            permissions=[cls.view_speditoer],
        )

        # Create some test data
        cls.speditoer = Speditør.objects.create(
            cvr=10001337,
            navn="speditoer1337",
        )

    def test_list(self):
        resp = self.client.get(
            reverse("api-1.0.0:speditør_list"),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            {"count": 1, "items": [{"cvr": 10001337, "navn": "speditoer1337"}]},
        )
