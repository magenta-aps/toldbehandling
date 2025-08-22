# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse
from ninja_extra.exceptions import PermissionDenied

from project.test_mixins import RestMixin, RestTestMixin
from project.util import json_dump
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
            "Vareafgiftssats("
            f"afgiftsgruppenummer={self.vareafgiftssats_data['afgiftsgruppenummer']}, "
            f"afgiftssats={self.vareafgiftssats_data['afgiftssats']}, "
            f"enhed={self.vareafgiftssats_data['enhed'].label}"
            ")",
        )

    def test_beregn_afgift_attr_error(self):
        vareafgiftssats = Vareafgiftssats(enhed="something-invalid-here")
        with self.assertRaises(AttributeError):
            vareafgiftssats.beregn_afgift(None)


class SatsAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_permissions = [
            Permission.objects.get(codename="view_afgiftstabel"),
            # Permission.objects.get(codename="change_afgiftstabel"),
        ]

        cls.user, cls.user_token, cls.user_refresh_token = RestMixin.make_user(
            username="payment-test-user",
            plaintext_password="testpassword1337",
            permissions=cls.user_permissions,
        )

        cls.test_afgiftstabel_1 = Afgiftstabel.objects.create(
            gyldig_fra=datetime(2022, 1, 1).replace(tzinfo=timezone.utc),
            gyldig_til=datetime(2023, 12, 31).replace(tzinfo=timezone.utc),
            kladde=False,
        )

        cls.test_afgiftstabel_2 = Afgiftstabel.objects.create(
            gyldig_fra=datetime(2023, 1, 1).replace(tzinfo=timezone.utc),
            gyldig_til=datetime(2024, 1, 1).replace(tzinfo=timezone.utc),
            kladde=False,
        )

    def test_list_afgiftstabeller_filter_gyldig_til__gt(self):
        endpoint = reverse("api-1.0.0:afgiftstabel_list")
        resp = self.client.get(
            f"{endpoint}?gyldig_til__gt=2023-12-31T00:00:00-02:00",
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )

        # Asserts
        self.assertEqual(resp.status_code, 200)
        resp_body = resp.json()

        self.assertEqual(resp_body["count"], 1)
        self.assertEqual(
            resp_body["items"],
            [
                {
                    "id": self.test_afgiftstabel_2.id,
                    "gyldig_fra": self.test_afgiftstabel_2.gyldig_fra.isoformat(),
                    "gyldig_til": None,  # OBS: see 'Afgiftstabel.on_update' on why this is None
                    "kladde": self.test_afgiftstabel_2.kladde,
                }
            ],
        )

    def test_list_afgiftstabeller_filter_gyldig_til__gte(self):
        endpoint = reverse("api-1.0.0:afgiftstabel_list")
        resp = self.client.get(
            f"{endpoint}?gyldig_til__gte=2024-01-01T00:00:00-02:00",
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )

        self.assertEqual(resp.status_code, 200)
        resp_body = resp.json()

        self.assertEqual(resp_body["count"], 1)
        self.assertEqual(
            resp_body["items"],
            [
                {
                    "id": self.test_afgiftstabel_2.id,
                    "gyldig_fra": self.test_afgiftstabel_2.gyldig_fra.isoformat(),
                    "gyldig_til": None,  # OBS: see 'Afgiftstabel.on_update' on why this is None
                    "kladde": self.test_afgiftstabel_2.kladde,
                }
            ],
        )

    @patch("sats.api.get_object_or_404")
    def test_update_afgiftstabel_draft_change_error(self, mock_get_object_or_404):
        self.user.user_permissions.add(
            Permission.objects.get(codename="change_afgiftstabel")
        )

        mock_get_object_or_404.return_value = self.test_afgiftstabel_1

        resp = self.client.patch(
            reverse(
                "api-1.0.0:afgiftstabel_update", args=[self.test_afgiftstabel_1.id]
            ),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
            data=json_dump({"kladde": True}),
        )

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(
            resp.json(),
            {"detail": "You do not have permission to perform this action."},
        )
        mock_get_object_or_404.assert_called_once_with(
            Afgiftstabel, id=self.test_afgiftstabel_1.id
        )
