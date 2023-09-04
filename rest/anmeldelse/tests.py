import json
from copy import deepcopy
from decimal import Decimal

from anmeldelse.models import Afgiftsanmeldelse, Varelinje
from django.test import TestCase
from django.urls import reverse
from project.test_mixins import RestMixin
from project.util import json_dump

from sats.models import Vareafgiftssats


class AfgiftsanmeldelseTest(RestMixin, TestCase):
    object_class = Afgiftsanmeldelse

    @property
    def list_full_function(self) -> str:
        return f"{self.object_class.__name__.lower()}_list_full"

    @property
    def get_full_function(self) -> str:
        return f"{self.object_class.__name__.lower()}_get_full"

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
                    "godkendt": None,
                }
            )
        return self._expected_object_data

    @property
    def sort_fields(self):
        return ("afsender", "modtager", "dato", "godkendt")

    @property
    def data_map(self):
        return {
            "afsender": self.afsender_data,
            "modtager": self.modtager_data,
            "fragtforsendelse": self.fragtforsendelse_data,
            "postforsendelse": self.postforsendelse_data,
        }

    def nest_expected_data(self, item):
        for key, value in self.data_map.items():
            if item.get(key, None) or item.get(key + "_id"):
                if key + "_id" in item:
                    del item[key + "_id"]
                item[key] = {
                    "id": getattr(self.afgiftsanmeldelse, key).id,
                    **self.unenumerate(value),
                }

    @property
    def expected_full_object_data(self):
        if not hasattr(self, "_expected_full_object_data"):
            self._expected_full_object_data = deepcopy(self.expected_object_data)
            self.nest_expected_data(self._expected_full_object_data)
        return self._expected_full_object_data

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
                    "godkendt": None,
                }
            )
        return self._expected_list_response_dict

    @property
    def expected_list_full_response_dict(self):
        if not hasattr(self, "_expected_list_full_response_dict"):
            self._expected_list_full_response_dict = deepcopy(
                self.expected_list_response_dict
            )
            self.nest_expected_data(self._expected_list_full_response_dict)
        return self._expected_list_full_response_dict

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
            f"Afgiftsanmeldelse(id={self.afgiftsanmeldelse.id})",
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
                {"id": self.varelinje.id, "afgiftsbeløb": "37.50"}
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

    def test_sammensat(self):
        personbiler = Vareafgiftssats.objects.create(
            afgiftstabel=self.afgiftstabel,
            afgiftsgruppenummer=72,
            vareart="PERSONBILER Afgiften svares med et fast beløb på 50.000 + 100 % af den del af fakturaværdien der overstiger 50.000 men ikke 150.000 + 125 % af resten.",
            enhed=Vareafgiftssats.Enhed.SAMMENSAT,
            minimumsbeløb=None,
            afgiftssats=Decimal(0),
            kræver_indførselstilladelse=False,
        )
        Vareafgiftssats.objects.create(
            overordnet=personbiler,
            afgiftstabel=self.afgiftstabel,
            afgiftsgruppenummer=7201,
            vareart="PERSONBILER, fast beløb på 50.000",
            enhed=Vareafgiftssats.Enhed.ANTAL,
            minimumsbeløb=None,
            afgiftssats=Decimal(50_000),
            kræver_indførselstilladelse=False,
        )
        Vareafgiftssats.objects.create(
            overordnet=personbiler,
            afgiftstabel=self.afgiftstabel,
            afgiftsgruppenummer=7202,
            vareart="PERSONBILER, 100% af den del af fakturaværdien der overstiger 50.000 men ikke 150.000",
            enhed=Vareafgiftssats.Enhed.PROCENT,
            segment_nedre=Decimal(50_000),
            segment_øvre=Decimal(150_000),
            minimumsbeløb=None,
            afgiftssats=Decimal(100),
            kræver_indførselstilladelse=False,
        )
        Vareafgiftssats.objects.create(
            overordnet=personbiler,
            afgiftstabel=self.afgiftstabel,
            afgiftsgruppenummer=7202,
            vareart="PERSONBILER, 125% af fakturaværdien der overstiger 150.000",
            enhed=Vareafgiftssats.Enhed.PROCENT,
            segment_nedre=Decimal(150_000),
            minimumsbeløb=None,
            afgiftssats=Decimal(150),
            kræver_indførselstilladelse=False,
        )
        varelinje1 = Varelinje.objects.create(
            afgiftssats=personbiler,
            afgiftsanmeldelse=self.afgiftsanmeldelse,
            kvantum=1,
            fakturabeløb=30_000,
        )
        self.assertEquals(varelinje1.afgiftsbeløb, Decimal(50_000))
        varelinje2 = Varelinje.objects.create(
            afgiftssats=personbiler,
            afgiftsanmeldelse=self.afgiftsanmeldelse,
            kvantum=1,
            fakturabeløb=65_000,
        )
        self.assertEquals(varelinje2.afgiftsbeløb, Decimal(50_000 + 1.0 * 15_000))
        varelinje3 = Varelinje.objects.create(
            afgiftssats=personbiler,
            afgiftsanmeldelse=self.afgiftsanmeldelse,
            kvantum=1,
            fakturabeløb=500_000,
        )
        self.assertEquals(
            varelinje3.afgiftsbeløb, Decimal(50_000 + 1.0 * 100_000 + 1.5 * 350_000)
        )
