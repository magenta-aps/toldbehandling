from decimal import Decimal

from anmeldelse.models import Afgiftsanmeldelse, Varelinje
from django.test import TestCase
from django.urls import reverse
from project.test_mixins import RestMixin
from project.util import json_dump


class AfgiftsanmeldelseTest(RestMixin, TestCase):
    object_class = Afgiftsanmeldelse
    unique_fields = ["anmeldelsesnummer"]

    def setUp(self) -> None:
        super().setUp()
        self.afgiftsanmeldelse_data.update(
            {
                "afsender_id": self.afsender.id,
                "modtager_id": self.modtager.id,
                "postforsendelse_id": self.postforsendelse.id,
            }
        )
        self.creation_data = self.afgiftsanmeldelse_data

    @property
    def expected_object_data(self):
        if not hasattr(self, "_expected_object_data"):
            self._expected_object_data = {}
            self._expected_object_data.update(self.creation_data)
            self._expected_object_data.update(
                {
                    "id": self.afgiftsanmeldelse.id,
                    "dato": self.afgiftsanmeldelse.dato.isoformat(),
                    "afgift_total": None,
                    "fragtforsendelse": None,
                    "afsender": self.afsender.id,
                    "modtager": self.modtager.id,
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
                    "id": self.afgiftsanmeldelse.id,
                    "dato": self.afgiftsanmeldelse.dato.isoformat(),
                    "afgift_total": None,
                    "fragtforsendelse": None,
                    "leverandørfaktura": f"/leverand%C3%B8rfakturaer/{self.afgiftsanmeldelse.id}/leverand%C3%B8rfaktura.pdf",
                }
            )
        return self._expected_list_response_dict

    def create_items(self):
        self.precreated_item = self.afgiftsanmeldelse

    invalid_itemdata = {
        "afsender_id": [1234, 0, -1, "a"],
        "modtager_id": [1234, 0, -1, "a"],
        "leverandørfaktura_nummer": ["123456789012345678901"],
        "indførselstilladelse": ["123456789012345678901"],
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
                    "modtager_betaler": True,
                    "leverandørfaktura": self.afgiftsanmeldelse_data[
                        "leverandørfaktura"
                    ],
                }
            )
        return self._update_object_data

    def test_str(self):
        self.assertEqual(
            str(self.afgiftsanmeldelse),
            f"Afgiftsanmeldelse(anmeldelsesnummer={self.afgiftsanmeldelse_data['anmeldelsesnummer']})",
        )

    def test_create_post_fragt_none(self):
        # Test at der kommer fejl 400 når både fraftforsendelse og postforsendelse mangler
        url = reverse(f"api-1.0.0:{self.create_function}")
        invalid_data = {**self.creation_data}
        del invalid_data["postforsendelse_id"]
        response = self.client.post(
            url,
            json_dump(invalid_data),
            HTTP_AUTHORIZATION=f"Bearer {self.authorized_access_token}",
            content_type="application/json",
        )
        self.assertIn(
            response.status_code,
            (400, 422),
            f"Attempted to reach CREATE API endpoint with invalid data, expected HTTP 400 or 422 for POST {url} with data {invalid_data}. Got HTTP {response.status_code}: {response.content}",
        )
        self.assertEqual(
            response.json(),
            {
                "__all__": [
                    "Fragtforsendelse og postforsendelse må ikke begge være None"
                ]
            },
        )

    def test_create_post_none(self):
        url = reverse(f"api-1.0.0:{self.create_function}")
        valid_data = {
            **self.creation_data,
            "fragtforsendelse_id": self.fragtforsendelse.id,
        }
        del valid_data["postforsendelse_id"]
        response = self.client.post(
            url,
            json_dump(valid_data),
            HTTP_AUTHORIZATION=f"Bearer {self.authorized_access_token}",
            content_type="application/json",
        )
        self.assertIn(
            response.status_code,
            (200, 201),
            f"Attempted to reach CREATE API endpoint, expected HTTP 200 or 201 for POST {url}. Got HTTP {response.status_code}: {response.content}",
        )


class VarelinjeTest(RestMixin, TestCase):
    plural_classname = "varelinjer"
    object_class = Varelinje
    unique_fields = []
    readonly_fields = []

    def setUp(self) -> None:
        super().setUp()
        self.varelinje_data.update(
            {
                "afgiftsanmeldelse_id": self.afgiftsanmeldelse.id,
                "afgiftssats_id": self.vareafgiftssats.id,
            }
        )
        self.creation_data = {**self.varelinje_data}

    def create_items(self):
        self.precreated_item = self.varelinje

    @classmethod
    def alter_value(cls, key, value):
        # Change value a little for lookup, so it's incorrect but still the right type
        # This is used to check that the changed value does not find the object
        if key in ("fakturabeløb", "afgiftsbeløb"):
            return str(Decimal(value) + Decimal(15))
        return super().alter_value(key, value)

    @property
    def expected_object_data(self):
        # Expected dict for object after create
        if not hasattr(self, "_expected_object_data"):
            self._expected_object_data = {}
            self._expected_object_data.update(self.strip_id(self.creation_data))
            self._expected_object_data.update(
                {"id": self.varelinje.id, "afgiftsbeløb": None}
            )
        return self._expected_object_data

    @property
    def expected_list_response_dict(self):
        if not hasattr(self, "_expected_list_response_dict"):
            self._expected_list_response_dict = {}
            self._expected_list_response_dict.update(self.strip_id(self.creation_data))
            self._expected_list_response_dict.update(
                {
                    "id": self.varelinje.id,
                }
            )
        return self._expected_list_response_dict

    invalid_itemdata = {
        "kvantum": ["a", -1],
        "fakturabeløb": ["a", -1],
        "afgiftsanmeldelse_id": ["a", -1, 9999],
        "afgiftssats_id": ["a", -1, 9999],
    }

    @property
    def update_object_data(self):
        if not hasattr(self, "_update_object_data"):
            self._update_object_data = {
                key: value
                for key, value in self.expected_object_data.items()
                if value is not None
            }
        return self._update_object_data

    def test_str(self):
        self.assertEqual(
            str(self.varelinje),
            f"Varelinje(afgiftssats=Vareafgiftssats(afgiftsgruppenummer={self.vareafgiftssats_data['afgiftsgruppenummer']}, afgiftssats={self.vareafgiftssats_data['afgiftssats']}, enhed={self.vareafgiftssats_data['enhed'].label}), fakturabeløb={self.varelinje_data['fakturabeløb']})",
        )
