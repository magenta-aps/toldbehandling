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

    @property
    def sort_fields(self):
        return ("gyldig_fra", "gyldig_til", "kladde")

    @classmethod
    def alter_value(cls, key, value):
        # Change value a little for lookup, so it's incorrect but still the right type
        # This is used to check that the changed value does not find the object
        if key.startswith("gyldig_fra") or key.startswith("gyldig_til"):
            if key.endswith("lt") or key.endswith("lte"):
                dt = timedelta(days=-100)
            else:
                dt = timedelta(days=100)
            newdate = date.fromisoformat(value) + dt
            return newdate.isoformat()
        return super().alter_value(key, value)

    invalid_itemdata = {"gyldig_til": [-1, "a", "2020-13-13"], "kladde": [-1, "foo"]}
    valid_itemdata = {}
    unique_fields = []

    @property
    def filter_data(self):
        return {
            "gyldig_fra__gt": (date.today() - timedelta(days=20)).isoformat(),
            "gyldig_fra__lt": (date.today() + timedelta(days=20)).isoformat(),
            "gyldig_fra__gte": (date.today()).isoformat(),
            "gyldig_fra__lte": (date.today()).isoformat(),
        }

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
        return self._update_object_data

    def test_str(self):
        self.assertEqual(
            str(self.afgiftstabel),
            f"Afgiftstabel(gyldig_fra={date.today().isoformat()}, gyldig_til={None}, kladde={True})",
        )

    def test_update_gyldig_til(self):
        # Tjek at gyldig_til opdateres automatisk
        tabel1 = Afgiftstabel.objects.create(gyldig_fra=date(2020, 1, 1), kladde=False)
        tabel2 = Afgiftstabel.objects.create(gyldig_fra=date(2021, 1, 1), kladde=False)
        tabel3 = Afgiftstabel.objects.create(gyldig_fra=date(2022, 1, 1), kladde=False)
        tabeller = [tabel1, tabel2, tabel3]
        for tabel in tabeller:
            tabel.refresh_from_db()
        self.assertEquals(tabel1.gyldig_til, date(2020, 12, 31))
        self.assertEquals(tabel2.gyldig_til, date(2021, 12, 31))
        self.assertEquals(tabel3.gyldig_til, None)

        # Indsæt ny tabel midt i sekvensen og tjek at gyldig_til opdateres
        tabel4 = Afgiftstabel.objects.create(gyldig_fra=date(2021, 7, 1), kladde=False)
        tabeller.append(tabel4)
        for tabel in tabeller:
            tabel.refresh_from_db()
        self.assertEquals(tabel1.gyldig_til, date(2020, 12, 31))
        self.assertEquals(tabel2.gyldig_til, date(2021, 6, 30))
        self.assertEquals(tabel3.gyldig_til, None)
        self.assertEquals(tabel4.gyldig_til, date(2021, 12, 31))

        # Flyt tabel til andet sted i sekvensen og tjek at gyldig_til opdateres
        tabel4.gyldig_fra = date(2020, 3, 10)
        tabel4.save()
        for tabel in tabeller:
            tabel.refresh_from_db()
        self.assertEquals(tabel1.gyldig_til, date(2020, 3, 9))
        self.assertEquals(tabel2.gyldig_til, date(2021, 12, 31))
        self.assertEquals(tabel3.gyldig_til, None)
        self.assertEquals(tabel4.gyldig_til, date(2020, 12, 31))


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
                    "minimumsbeløb": None,
                    "overordnet": None,
                    "segment_nedre": None,
                    "segment_øvre": None,
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
                    "minimumsbeløb": None,
                    "overordnet": None,
                    "segment_nedre": None,
                    "segment_øvre": None,
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
