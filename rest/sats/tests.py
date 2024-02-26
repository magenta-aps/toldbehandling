# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from django.test import TestCase
from project.test_mixins import RestTestMixin
from sats.models import Afgiftstabel, Vareafgiftssats


class AfgiftstabelTest(RestTestMixin, TestCase):
    __test__ = True
    object_class = Afgiftstabel
    has_delete = True

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
            newdate = datetime.fromisoformat(value) + dt
            return newdate.isoformat()
        return super().alter_value(key, value)

    invalid_itemdata = {"gyldig_til": [-1, "a", "2020-13-13"], "kladde": [-1, "foo"]}
    valid_itemdata = {}
    unique_fields = []

    @property
    def filter_data(self):
        return {
            "gyldig_fra__gt": (
                self.afgiftstabel.gyldig_fra - timedelta(days=20)
            ).isoformat(),
            "gyldig_fra__lt": (
                self.afgiftstabel.gyldig_fra + timedelta(days=20)
            ).isoformat(),
            "gyldig_fra__gte": (self.afgiftstabel.gyldig_fra).isoformat(),
            "gyldig_fra__lte": (self.afgiftstabel.gyldig_fra).isoformat(),
        }

    @property
    def expected_object_data(self):
        return {
            "id": self.afgiftstabel.id,
            **self.creation_data,
            "gyldig_fra": self.afgiftstabel.gyldig_fra.isoformat(),
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
            f"Afgiftstabel(gyldig_fra={self.afgiftstabel_data['gyldig_fra']}, gyldig_til={None}, kladde={True})",
        )

    def test_update_gyldig_til(self):
        # Tjek at gyldig_til opdateres automatisk
        tabel1 = Afgiftstabel.objects.create(
            gyldig_fra=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc), kladde=False
        )
        tabel2 = Afgiftstabel.objects.create(
            gyldig_fra=datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc), kladde=False
        )
        tabel3 = Afgiftstabel.objects.create(
            gyldig_fra=datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc), kladde=False
        )
        tabeller = [tabel1, tabel2, tabel3]
        for tabel in tabeller:
            tabel.refresh_from_db()
        self.assertEquals(
            tabel1.gyldig_til, datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        )
        self.assertEquals(
            tabel2.gyldig_til, datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        )
        self.assertEquals(tabel3.gyldig_til, None)

        # Indsæt ny tabel midt i sekvensen og tjek at gyldig_til opdateres
        tabel4 = Afgiftstabel.objects.create(
            gyldig_fra=datetime(2021, 7, 1, 0, 0, 0, tzinfo=timezone.utc), kladde=False
        )
        tabeller.append(tabel4)
        for tabel in tabeller:
            tabel.refresh_from_db()
        self.assertEquals(
            tabel1.gyldig_til, datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        )
        self.assertEquals(
            tabel2.gyldig_til, datetime(2021, 7, 1, 0, 0, 0, tzinfo=timezone.utc)
        )
        self.assertEquals(tabel3.gyldig_til, None)
        self.assertEquals(
            tabel4.gyldig_til, datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        )

        # Flyt tabel til andet sted i sekvensen og tjek at gyldig_til opdateres
        tabel4.gyldig_fra = datetime(2020, 3, 10, 0, 0, 0, tzinfo=timezone.utc)
        tabel4.save()
        for tabel in tabeller:
            tabel.refresh_from_db()
        self.assertEquals(
            tabel1.gyldig_til, datetime(2020, 3, 10, 0, 0, 0, tzinfo=timezone.utc)
        )
        self.assertEquals(
            tabel2.gyldig_til, datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        )
        self.assertEquals(tabel3.gyldig_til, None)
        self.assertEquals(
            tabel4.gyldig_til, datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        )


class VareafgiftssatsTest(RestTestMixin, TestCase):
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
        "vareart_da": [-1, 9001],
        "vareart_kl": [-1, 9001],
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

    # Expected item from REST interface
    @property
    def expected_response_dict(self):
        if not hasattr(self, "_expected_response_dict"):
            self._expected_response_dict = {}
            self._expected_response_dict.update(self.strip_id(self.creation_data))
            self._expected_response_dict.update(
                {
                    "id": self.vareafgiftssats.id,
                    "minimumsbeløb": None,
                    "overordnet": None,
                    "segment_nedre": None,
                    "segment_øvre": None,
                }
            )
        return self._expected_response_dict

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
