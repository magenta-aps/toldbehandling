from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from project.test_mixins import RestMixin
from sats.models import Afgiftstabel, Vareafgiftssats


class AfgiftstabelTest(RestMixin, TestCase):
    __test__ = True
    object_class = Afgiftstabel

    def setUp(self) -> None:
        super().setUp()
        self.creation_data = self.afgiftstabel_data

    def create_items(self):
        self.precreated_item = self.afgiftstabel

    @classmethod
    def alter_value(cls, key, value):
        # Change value a little for lookup, so it's incorrect but still the right type
        # This is used to check that the changed value does not find the object
        if key in ("gyldig_fra", "gyldig_til"):
            newdate = date.fromisoformat(value) + timedelta(days=100)
            return newdate.isoformat()
        return super().alter_value(key, value)

    invalid_itemdata = {"gyldig_til": [-1, "a", "2020-13-13"], "kladde": [-1, "foo"]}
    valid_itemdata = {}
    unique_fields = []

    @property
    def expected_object_data(self):
        return {
            "id": self.afgiftstabel.id,
            **self.creation_data,
            "gyldig_fra": date.today().isoformat(),
            "gyldig_til": None,
            "kladde": True,
        }

    @property
    def expected_list_response_dict(self):
        return {
            "id": self.afgiftstabel.id,
            **self.creation_data,
            "gyldig_fra": date.today().isoformat(),
            "gyldig_til": None,
            "kladde": True,
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
                    "gyldig_til": (date.today() + timedelta(days=200)).isoformat(),
                }
            )
        return self._update_object_data

    def test_str(self):
        self.assertEqual(
            str(self.afgiftstabel),
            f"Afgiftstabel(gyldig_fra={date.today().isoformat()}, gyldig_til={None}, kladde={True})",
        )


class VareafgiftssatsTest(RestMixin, TestCase):
    __test__ = True
    plural_classname = "vareafgiftssatser"
    object_class = Vareafgiftssats

    def setUp(self) -> None:
        super().setUp()
        self.vareafgiftssats_data.update(
            {
                "afgiftstabel_id": self.afgiftstabel.id,
            }
        )
        self.creation_data = self.vareafgiftssats_data

    def create_items(self):
        self.precreated_item = self.vareafgiftssats

    @classmethod
    def alter_value(cls, key, value):
        # Change value a little for lookup, so it's incorrect but still the right type
        # This is used to check that the changed value does not find the object
        if key in ("afgiftssats",):
            return str(Decimal(value) + Decimal(30))
        return super().alter_value(key, value)

    invalid_itemdata = {
        "vareart": [-1, 9001],
        "afgiftsgruppenummer": [-1],
        "enhed": ["A", 4],
        "afgiftssats": [9001],
    }
    valid_itemdata = {}
    unique_fields = []

    @property
    def expected_object_data(self):
        if not hasattr(self, "_expected_object_data"):
            self._expected_object_data = {}
            self._expected_object_data.update(self.creation_data)
            self._expected_object_data.update(
                {
                    "id": self.vareafgiftssats.id,
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
                    "id": self.vareafgiftssats.id,
                }
            )
        return self._expected_list_response_dict

    @property
    def update_object_data(self):
        if not hasattr(self, "_update_object_data"):
            self._update_object_data = {
                key: value
                for key, value in self.expected_object_data.items()
                if value is not None
            }
            self._update_object_data.update({})
        return self._update_object_data

    def test_str(self):
        self.assertEqual(
            str(self.vareafgiftssats),
            f"Vareafgiftssats(afgiftsgruppenummer={self.vareafgiftssats_data['afgiftsgruppenummer']}, afgiftssats={self.vareafgiftssats_data['afgiftssats']}, enhed={self.vareafgiftssats_data['enhed'].label})",
        )
