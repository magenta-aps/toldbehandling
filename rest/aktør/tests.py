# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from aktør.models import Afsender, Modtager
from django.test import TestCase
from project.test_mixins import RestMixin


class AfsenderTest(RestMixin, TestCase):
    __test__ = True
    object_class = Afsender

    def setUp(self) -> None:
        super().setUp()
        self.creation_data = self.afsender_data

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

    @property
    def expected_object_data(self):
        return {"id": self.afsender.id, **self.creation_data}

    @property
    def expected_list_response_dict(self):
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


class ModtagerTest(RestMixin, TestCase):
    __test__ = True
    plural_classname = "modtagere"
    object_class = Modtager

    def setUp(self) -> None:
        super().setUp()
        self.creation_data = self.modtager_data

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
        "indførselstilladelse": 123,
    }

    @property
    def expected_object_data(self):
        return {"id": self.modtager.id, **self.creation_data}

    @property
    def expected_list_response_dict(self):
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
                    "indførselstilladelse": 124,
                }
            )
        return self._update_object_data

    def test_str(self):
        self.assertEqual(
            str(self.modtager),
            f"Modtager(navn={self.modtager_data['navn']}, cvr={self.modtager_data['cvr']})",
        )
