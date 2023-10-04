# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from django.test import TestCase
from forsendelse.models import Postforsendelse, Fragtforsendelse
from project.test_mixins import RestMixin


class PostforsendelseTest(RestMixin, TestCase):
    object_class = Postforsendelse
    unique_fields = []
    exclude_fields = ["oprettet_af"]
    has_delete = True

    def setUp(self) -> None:
        super().setUp()
        self.creation_data = self.postforsendelse_data

    @property
    def expected_object_data(self):
        if not hasattr(self, "_expected_object_data"):
            self._expected_object_data = {}
            self._expected_object_data.update(self.strip_id(self.creation_data))
            self._expected_object_data.update(
                {
                    "id": self.postforsendelse.id,
                }
            )
        return self._expected_object_data

    @property
    def expected_list_response_dict(self):
        if not hasattr(self, "_expected_list_response_dict"):
            self._expected_list_response_dict = {}
            self._expected_list_response_dict.update(self.strip_id(self.creation_data))
            self._expected_list_response_dict.update(
                {
                    "id": self.postforsendelse.id,
                }
            )
        return self._expected_list_response_dict

    def create_items(self):
        self.precreated_item = self.postforsendelse

    invalid_itemdata = {
        "forsendelsestype": [1234, 0, -1, "a", "Q"],
        "postforsendelsesnummer": ["123456789012345678901"],
    }

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
                    "postforsendelsesnummer": "5555",
                }
            )
        return self._update_object_data

    def test_str(self):
        string = str(self.postforsendelse)
        self.assertIn(self.postforsendelse_data["postforsendelsesnummer"], string)
        self.assertIn(str(self.postforsendelse_data["forsendelsestype"].label), string)
        self.assertIn(self.postforsendelse_data["afsenderbykode"], string)


class FragtforsendelseTest(RestMixin, TestCase):
    plural_classname = "fragtforsendelser"
    object_class = Fragtforsendelse
    unique_fields = []
    exclude_fields = ["oprettet_af"]
    has_delete = True

    def setUp(self) -> None:
        super().setUp()
        self.creation_data = self.fragtforsendelse_data

    @property
    def expected_object_data(self):
        if not hasattr(self, "_expected_object_data"):
            self._expected_object_data = {}
            self._expected_object_data.update(self.strip_id(self.creation_data))
            self._expected_object_data.update(
                {
                    "id": self.fragtforsendelse.id,
                }
            )
        return self._expected_object_data

    @property
    def expected_list_response_dict(self):
        if not hasattr(self, "_expected_list_response_dict"):
            self._expected_list_response_dict = {}
            self._expected_list_response_dict.update(self.strip_id(self.creation_data))
            self._expected_list_response_dict.update(
                {
                    "id": self.fragtforsendelse.id,
                }
            )
        return self._expected_list_response_dict

    def create_items(self):
        self.precreated_item = self.fragtforsendelse

    invalid_itemdata = {
        "forsendelsestype": [1234, 0, -1, "a", "Q"],
        "fragtbrevsnummer": ["123456789012345678901"],
        "fragtbrev": ["aaaa"],
    }

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
                    "fragtbrevsnummer": "5555",
                    "fragtbrev": self.fragtforsendelse_data["fragtbrev"],
                }
            )
        return self._update_object_data

    def test_str(self):
        string = str(self.fragtforsendelse)
        self.assertIn(self.fragtforsendelse_data["fragtbrevsnummer"], string)
        self.assertIn(str(self.fragtforsendelse_data["forsendelsestype"].label), string)
        self.assertIn(self.fragtforsendelse_data["forbindelsesnr"], string)
