# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import ANY, MagicMock, call, patch
from uuid import uuid4

from aktør.models import Afsender, Modtager
from anmeldelse.api import AfgiftsanmeldelseAPI
from anmeldelse.models import (
    Afgiftsanmeldelse,
    PrismeResponse,
    Varelinje,
    on_add_prismeresponse,
    on_delete_prismeresponse,
    privatafgiftsanmeldelse_upload_to,
)
from common.models import IndberetterProfile
from django.contrib.auth.models import Permission
from django.core.files.base import ContentFile
from django.db.models.signals import post_delete, post_save
from django.test import TestCase
from django.urls import reverse
from forsendelse.models import Postforsendelse
from project.test_mixins import RestMixin, RestTestMixin
from project.util import json_dump
from sats.models import Vareafgiftssats


class AnmeldelsesTestDataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.view_afgiftsanmeldelse_perm = Permission.objects.get(
            codename="view_afgiftsanmeldelse"
        )

        cls.add_afgiftsanmeldelse_perm = Permission.objects.get(
            codename="add_afgiftsanmeldelse"
        )

        cls.change_afgiftsanmeldelse_perm = Permission.objects.get(
            codename="change_afgiftsanmeldelse"
        )

        cls.view_historicalafgiftsanmeldelse = Permission.objects.get(
            codename="view_historicalafgiftsanmeldelse"
        )

        # User-1 (CVR)
        cls.user, cls.user_token, cls.user_refresh_token = RestMixin.make_user(
            username="payment-test-user",
            plaintext_password="testpassword1337",
            permissions=[
                cls.view_afgiftsanmeldelse_perm,
                cls.add_afgiftsanmeldelse_perm,
                cls.change_afgiftsanmeldelse_perm,
                cls.view_historicalafgiftsanmeldelse,
            ],
        )

        cls.indberetter = IndberetterProfile.objects.create(
            user=cls.user,
            cvr="13371337",
            api_key=uuid4(),
        )

        # Afsender & Modtager
        cls.afsender = Afsender.objects.create(
            **{
                "navn": "Testfirma 1",
                "adresse": "Testvej 42",
                "postnummer": 1234,
                "by": "TestBy",
                "postbox": "123",
                "telefon": "123456",
                "cvr": 12345678,
                "kladde": False,
            }
        )

        cls.modtager = Modtager.objects.create(
            **{
                "navn": "Testfirma 1",
                "adresse": "Testvej 42",
                "postnummer": 1234,
                "by": "TestBy",
                "postbox": "123",
                "telefon": "123456",
                "cvr": 12345678,
                "kreditordning": True,
                "kladde": False,
            }
        )

        #  Postforsendelse

        cls.postforsendelse, _ = Postforsendelse.objects.get_or_create(
            postforsendelsesnummer="1234",
            oprettet_af=cls.user,
            defaults={
                "forsendelsestype": Postforsendelse.Forsendelsestype.SKIB,
                "afsenderbykode": "8200",
                "afgangsdato": "2023-11-03",
                "kladde": False,
            },
        )

        # Afgiftsanmeldelse
        cls.afgiftsanmeldelse = Afgiftsanmeldelse.objects.create(
            **{
                "afsender_id": cls.afsender.id,
                "modtager_id": cls.modtager.id,
                "postforsendelse_id": cls.postforsendelse.id,
                "leverandørfaktura_nummer": "12345",
                "betales_af": "afsender",
                "indførselstilladelse": "abcde",
                "betalt": False,
                "fuldmagtshaver": None,
                "status": "ny",
                "oprettet_af": cls.user,
                "tf3": False,
            }
        )


# Tests


class AfgiftsanmeldelseTest(RestTestMixin, TestCase):
    object_class = Afgiftsanmeldelse
    exclude_fields = ["oprettet_af"]
    object_restriction = True

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
        self.calculated_fields = {
            "beregnet_faktureringsdato": "2023-11-30",
            "oprettet_af": {
                "id": self.authorized_user.id,
                "username": "testuser1",
                "first_name": "",
                "last_name": "",
                "email": "",
                "is_superuser": False,
                "groups": [],
                "permissions": [
                    "anmeldelse.add_afgiftsanmeldelse",
                    "anmeldelse.approve_reject_anmeldelse",
                    "anmeldelse.change_afgiftsanmeldelse",
                    "anmeldelse.delete_afgiftsanmeldelse",
                    "anmeldelse.view_afgiftsanmeldelse",
                    "anmeldelse.view_all_anmeldelse",
                    "forsendelse.view_all_fragtforsendelser",
                    "forsendelse.view_all_postforsendelser",
                ],
                "indberetter_data": None,
                "twofactor_enabled": False,
            },
            "oprettet_på_vegne_af": None,
            # "afgift_total": '0',
        }

    # Expected object in the database as dict
    @property
    def expected_object_data(self):
        if not hasattr(self, "_expected_object_data"):
            self._expected_object_data = {}
            self._expected_object_data.update(self.creation_data)
            self._expected_object_data.update(
                {
                    "id": self.afgiftsanmeldelse.id,
                    "dato": self.afgiftsanmeldelse.dato.isoformat(),
                    "afgift_total": "0.00",
                    "fragtforsendelse": None,
                    "afsender": self.afsender.id,
                    "modtager": self.modtager.id,
                    "status": "ny",
                    "oprettet_på_vegne_af": None,
                    "toldkategori": None,
                    "tf3": False,
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
                    "id": self.afgiftsanmeldelse.id,
                    "dato": self.afgiftsanmeldelse.dato.isoformat(),
                    "afgift_total": "0.00",
                    "fragtforsendelse": None,
                    "leverandørfaktura": f"/leverand%C3%B8rfakturaer/{self.afgiftsanmeldelse.id}/leverand%C3%B8rfaktura.pdf",
                    "status": "ny",
                    "toldkategori": None,
                    "tf3": False,
                    **self.calculated_fields,
                }
            )
        return self._expected_response_dict

    @property
    def sort_fields(self):
        return ("afsender", "modtager", "dato", "status")

    @property
    def data_map(self):
        return {
            "afsender": self.afsender_data_expected,
            "modtager": self.modtager_data_expected,
            "fragtforsendelse": self.fragtforsendelse_data,
            "postforsendelse": self.postforsendelse_data,
        }

    def nest_expected_data(self, item):
        for key, value in self.data_map.items():
            if item.get(key) or item.get(key + "_id"):
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
            self._expected_full_object_data.update(self.calculated_fields)
            self.nest_expected_data(self._expected_full_object_data)

        return self._expected_full_object_data

    @property
    def expected_list_full_response_dict(self):
        if not hasattr(self, "_expected_list_full_response_dict"):
            self._expected_list_full_response_dict = deepcopy(
                self.expected_response_dict
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
                    "betales_af": "modtager",
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

    def test_approved_only(self):
        afgiftsanmeldelse = self.afgiftsanmeldelse
        url = reverse(f"api-1.0.0:{self.list_function}")
        response = self.client.get(
            url, HTTP_AUTHORIZATION=f"Bearer {self.approvedonly_access_token}"
        )
        data = response.json()
        self.assertEquals(data["count"], 0)
        self.assertEquals(data["items"], [])

        self._afgiftsanmeldelse.status = "godkendt"
        self._afgiftsanmeldelse.save()

        response = self.client.get(
            url, HTTP_AUTHORIZATION=f"Bearer {self.approvedonly_access_token}"
        )
        data = response.json()
        self.assertEquals(data["count"], 1)
        self.assertEquals(
            data["items"][0], {**self.expected_response_dict, "status": "godkendt"}
        )

    def test_delete_success(self):
        # Test delete of "ny"
        afgiftsanmeldelse_new = Afgiftsanmeldelse.objects.create(
            **{
                **self.afgiftsanmeldelse_data,
                "status": "ny",
                "oprettet_af": self.authorized_user,
            }
        )

        resp_delete_new = self.client.delete(
            reverse(
                f"api-1.0.0:{self.delete_function}", args=[afgiftsanmeldelse_new.id]
            ),
            HTTP_AUTHORIZATION=f"Bearer {self.authorized_access_token}",
        )
        self.assertEquals(resp_delete_new.status_code, 200)

        # Test delete of "kladde"
        afgiftsanmeldelse_kladde = Afgiftsanmeldelse.objects.create(
            **{
                **self.afgiftsanmeldelse_data,
                "status": "kladde",
                "oprettet_af": self.authorized_user,
            }
        )
        resp_delete_kladde = self.client.delete(
            reverse(
                f"api-1.0.0:{self.delete_function}", args=[afgiftsanmeldelse_kladde.id]
            ),
            HTTP_AUTHORIZATION=f"Bearer {self.authorized_access_token}",
        )
        self.assertEquals(resp_delete_kladde.status_code, 200)

        # Assert that all objects are deleted
        self.assertEquals(Afgiftsanmeldelse.objects.count(), 0)

    def test_delete_fail(self):
        invalid_statuses = ["godkendt", "afsluttet", "afvist"]
        for idx, invalid_status in enumerate(invalid_statuses):
            postforsendelse = Postforsendelse.objects.create(
                **{
                    **self.postforsendelse_data,
                    "postforsendelsesnummer": f'{self.postforsendelse_data["postforsendelsesnummer"]}{str(idx)}',
                    "oprettet_af": self.authorized_user,
                }
            )

            afgiftsanmeldelse = Afgiftsanmeldelse.objects.create(
                **{
                    **self.afgiftsanmeldelse_data,
                    "status": invalid_status,
                    "oprettet_af": self.authorized_user,
                    "postforsendelse_id": postforsendelse.id,
                }
            )

            resp_delete = self.client.delete(
                reverse(
                    f"api-1.0.0:{self.delete_function}", args=[afgiftsanmeldelse.id]
                ),
                HTTP_AUTHORIZATION=f"Bearer {self.authorized_access_token}",
            )
            self.assertEquals(resp_delete.status_code, 403)

        self.assertEquals(Afgiftsanmeldelse.objects.count(), len(invalid_statuses))

    def test_afgiftsanmeldelse_upload_to(self):
        result = privatafgiftsanmeldelse_upload_to(self.afgiftsanmeldelse, "test.pdf")
        self.assertEquals(
            result, f"privatfakturaer/{self.afgiftsanmeldelse.id}/test.pdf"
        )

    def test_beregn_faktureringsdato_told_categories(self):
        self.afgiftsanmeldelse.toldkategori = "70"
        result = Afgiftsanmeldelse.beregn_faktureringsdato(self.afgiftsanmeldelse)
        self.assertEqual(result, date(2023, 12, 20))

        self.afgiftsanmeldelse.toldkategori = "76"
        result = Afgiftsanmeldelse.beregn_faktureringsdato(self.afgiftsanmeldelse)
        self.assertEqual(result, date(2023, 12, 14))

    def test_receiver_on_add_prismeresponse(self):
        # Connect the signal manually to ensure it's being tested
        post_save.connect(
            on_add_prismeresponse,
            sender=PrismeResponse,
            dispatch_uid="test_on_add_prismeresponse",
        )

        prismeresponse = PrismeResponse.objects.create(
            afgiftsanmeldelse=self.afgiftsanmeldelse,
            rec_id=123456,
            tax_notification_number=654321,
            delivery_date=datetime.now(UTC) + timedelta(days=30),
        )

        self.afgiftsanmeldelse.refresh_from_db()

        self.assertEqual(self.afgiftsanmeldelse.status, "afsluttet")

        # Disconnect signal after test to clean up
        post_save.disconnect(
            on_add_prismeresponse,
            sender=PrismeResponse,
            dispatch_uid="test_on_add_prismeresponse",
        )

    def test_receiver_on_delete_prismeresponse(self):
        prismeresponse_1 = PrismeResponse.objects.create(
            afgiftsanmeldelse=self.afgiftsanmeldelse,
            rec_id=123456,
            tax_notification_number=654321,
            delivery_date=datetime.now(UTC) + timedelta(days=30),
        )

        post_delete.connect(
            on_delete_prismeresponse,
            sender=PrismeResponse,
            dispatch_uid="test_on_delete_prismeresponse",
        )

        prismeresponse_1.delete()

        self.afgiftsanmeldelse.refresh_from_db()
        self.assertEqual(self.afgiftsanmeldelse.status, "godkendt")

        post_delete.disconnect(
            on_delete_prismeresponse,
            sender=PrismeResponse,
            dispatch_uid="test_on_delete_prismeresponse",
        )


class VarelinjeTest(RestTestMixin, TestCase):
    plural_classname = "varelinjer"
    object_class = Varelinje
    unique_fields = []
    readonly_fields = []
    has_delete = True

    def setUp(self) -> None:
        super().setUp()
        self.varelinje_data.update(
            {
                "afgiftsanmeldelse_id": self.afgiftsanmeldelse.id,
                "privatafgiftsanmeldelse_id": None,
                "vareafgiftssats_id": self.vareafgiftssats.id,
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

    # Expected object in the database as dict
    @property
    def expected_object_data(self):
        # Expected dict for object after create
        if not hasattr(self, "_expected_object_data"):
            self._expected_object_data = {}
            self._expected_object_data.update(self.strip_id(self.creation_data))
            self._expected_object_data.update(
                {
                    "id": self.varelinje.id,
                    "afgiftsbeløb": "37.50",
                    "kladde": False,
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
                    "id": self.varelinje.id,
                    "kladde": False,
                }
            )
        return self._expected_response_dict

    invalid_itemdata = {
        "antal": ["a", -1],
        "fakturabeløb": ["a", -1],
        "afgiftsanmeldelse_id": ["a", -1, 9999],
        "vareafgiftssats_id": ["a", -1, 9999],
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
            f"Varelinje(vareafgiftssats=Vareafgiftssats(afgiftsgruppenummer={self.vareafgiftssats_data['afgiftsgruppenummer']}, afgiftssats={self.vareafgiftssats_data['afgiftssats']}, enhed={self.vareafgiftssats_data['enhed'].label}), fakturabeløb={self.varelinje_data['fakturabeløb']})",
        )

    def test_sammensat(self):
        personbiler = Vareafgiftssats.objects.create(
            afgiftstabel=self.afgiftstabel,
            afgiftsgruppenummer=72,
            vareart_da="PERSONBILER Afgiften svares med et fast beløb på 50.000 + 100 % af den del af fakturaværdien der overstiger 50.000 men ikke 150.000 + 125 % af resten.",
            vareart_kl="PERSONBILER Afgiften svares med et fast beløb på 50.000 + 100 % af den del af fakturaværdien der overstiger 50.000 men ikke 150.000 + 125 % af resten.",
            enhed=Vareafgiftssats.Enhed.SAMMENSAT,
            minimumsbeløb=None,
            afgiftssats=Decimal(0),
            kræver_indførselstilladelse=False,
        )
        Vareafgiftssats.objects.create(
            overordnet=personbiler,
            afgiftstabel=self.afgiftstabel,
            afgiftsgruppenummer=7201,
            vareart_da="PERSONBILER, fast beløb på 50.000",
            vareart_kl="PERSONBILER, fast beløb på 50.000",
            enhed=Vareafgiftssats.Enhed.ANTAL,
            minimumsbeløb=None,
            afgiftssats=Decimal(50_000),
            kræver_indførselstilladelse=False,
        )
        Vareafgiftssats.objects.create(
            overordnet=personbiler,
            afgiftstabel=self.afgiftstabel,
            afgiftsgruppenummer=7202,
            vareart_da="PERSONBILER, 100% af den del af fakturaværdien der overstiger 50.000 men ikke 150.000",
            vareart_kl="PERSONBILER, 100% af den del af fakturaværdien der overstiger 50.000 men ikke 150.000",
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
            vareart_da="PERSONBILER, 125% af fakturaværdien der overstiger 150.000",
            vareart_kl="PERSONBILER, 125% af fakturaværdien der overstiger 150.000",
            enhed=Vareafgiftssats.Enhed.PROCENT,
            segment_nedre=Decimal(150_000),
            minimumsbeløb=None,
            afgiftssats=Decimal(150),
            kræver_indførselstilladelse=False,
        )
        varelinje1 = Varelinje.objects.create(
            vareafgiftssats=personbiler,
            afgiftsanmeldelse=self.afgiftsanmeldelse,
            antal=1,
            fakturabeløb=30_000,
        )
        self.assertEquals(varelinje1.afgiftsbeløb, Decimal(50_000))
        varelinje2 = Varelinje.objects.create(
            vareafgiftssats=personbiler,
            afgiftsanmeldelse=self.afgiftsanmeldelse,
            antal=1,
            fakturabeløb=65_000,
        )
        self.assertEquals(varelinje2.afgiftsbeløb, Decimal(50_000 + 1.0 * 15_000))
        varelinje3 = Varelinje.objects.create(
            vareafgiftssats=personbiler,
            afgiftsanmeldelse=self.afgiftsanmeldelse,
            antal=1,
            fakturabeløb=500_000,
        )
        self.assertEquals(
            varelinje3.afgiftsbeløb, Decimal(50_000 + 1.0 * 100_000 + 1.5 * 350_000)
        )


class StatistikTest(RestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.afgiftsanmeldelse.status = "afsluttet"
        self.afgiftsanmeldelse.save()
        self.varelinje
        self.vareafgiftssats2 = Vareafgiftssats.objects.create(
            afgiftstabel=self.afgiftstabel,
            afgiftsgruppenummer=5678,
            vareart_da="Te",
            vareart_kl="Te",
            enhed=Vareafgiftssats.Enhed.KILOGRAM,
            minimumsbeløb=None,
            afgiftssats=Decimal(1000),
            kræver_indførselstilladelse=False,
        )
        self.varelinje2 = Varelinje.objects.create(
            vareafgiftssats=self.vareafgiftssats2,
            afgiftsanmeldelse=self.afgiftsanmeldelse,
            mængde=500,
            fakturabeløb=5000,
        )
        self.varelinje3 = Varelinje.objects.create(
            vareafgiftssats=self.vareafgiftssats,
            afgiftsanmeldelse=self.afgiftsanmeldelse,
            mængde=700,
            fakturabeløb=5000,
            antal=10,
        )
        self.varelinje4 = Varelinje.objects.create(
            vareafgiftssats=self.vareafgiftssats2,
            afgiftsanmeldelse=self.afgiftsanmeldelse,
            mængde=900,
            fakturabeløb=9000,
        )

    def test_statistik_access(self):
        url = reverse(f"api-1.0.0:statistik_get")
        response = self.client.get(url)
        self.assertEquals(response.status_code, 401)

    def test_statistik(self):
        url = reverse(f"api-1.0.0:statistik_get")
        response = self.client.get(
            url, HTTP_AUTHORIZATION=f"Bearer {self.authorized_access_token}"
        )
        data = response.json()["items"]
        self.assertEquals(len(data), 2)
        # Sorteret efter afgiftsgruppenummer
        self.assertEquals(
            data[0],
            {
                # self.varelinje3 + self.varelinje_data
                "sum_afgiftsbeløb": "1787.50",
                "afgiftsgruppenummer": 1234,
                "vareart_da": "Kaffe",
                "vareart_kl": "Kaffe",
                "enhed": "kg",
                "sum_antal": 11,
                "sum_mængde": "715.000",
            },
        )
        self.assertEquals(
            data[1],
            {
                "sum_afgiftsbeløb": "1400000.00",
                "afgiftsgruppenummer": 5678,
                "vareart_da": "Te",
                "vareart_kl": "Te",
                "enhed": "kg",
                "sum_antal": 0,
                "sum_mængde": "1400.000",
            },
        )


class AfgiftsanmeldelseAPITest(AnmeldelsesTestDataMixin, TestCase):
    maxDiff = None

    def test_create_kladde(self):
        postforsendelse_local, _ = Postforsendelse.objects.get_or_create(
            postforsendelsesnummer="112233",
            oprettet_af=self.user,
            defaults={
                "forsendelsestype": Postforsendelse.Forsendelsestype.SKIB,
                "afsenderbykode": "8200",
                "afgangsdato": "2023-11-03",
                "kladde": False,
            },
        )

        resp = self.client.post(
            reverse("api-1.0.0:afgiftsanmeldelse_create"),
            data=json_dump(
                {
                    "afsender_id": self.afsender.id,
                    "modtager_id": self.modtager.id,
                    "postforsendelse_id": postforsendelse_local.id,
                    "kladde": True,
                }
            ),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

        new_row_id = int(resp.json()["id"])
        afgiftsanmeldelse = Afgiftsanmeldelse.objects.get(id=new_row_id)
        self.assertEqual(afgiftsanmeldelse.status, "kladde")

    def test_create_betales_af_blank(self):
        postforsendelse_local, _ = Postforsendelse.objects.get_or_create(
            postforsendelsesnummer="223344",
            oprettet_af=self.user,
            defaults={
                "forsendelsestype": Postforsendelse.Forsendelsestype.SKIB,
                "afsenderbykode": "8200",
                "afgangsdato": "2023-11-03",
                "kladde": False,
            },
        )

        resp = self.client.post(
            reverse("api-1.0.0:afgiftsanmeldelse_create"),
            data=json_dump(
                {
                    "afsender_id": self.afsender.id,
                    "modtager_id": self.modtager.id,
                    "postforsendelse_id": postforsendelse_local.id,
                    "leverandørfaktura_nummer": "12345678901234567890",
                    "betales_af": "",
                }
            ),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

        new_row_id = int(resp.json()["id"])
        afgiftsanmeldelse = Afgiftsanmeldelse.objects.get(id=new_row_id)
        self.assertEqual(afgiftsanmeldelse.betales_af, None)

    def test_get_history(self):
        # Invoke the endpoint
        resp = self.client.get(
            reverse(
                "api-1.0.0:afgiftsanmeldelse_get_history",
                args=[self.afgiftsanmeldelse.id],
            ),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            {
                "count": 1,
                "items": [
                    {
                        "id": self.afgiftsanmeldelse.id,
                        "afsender": self.afsender.id,
                        "modtager": self.modtager.id,
                        "fragtforsendelse": None,
                        "postforsendelse": self.postforsendelse.id,
                        "leverandørfaktura_nummer": "12345",
                        "leverandørfaktura": "",
                        "betales_af": "afsender",
                        "indførselstilladelse": "abcde",
                        "afgift_total": "0.00",
                        "betalt": False,
                        "dato": ANY,
                        "status": "ny",
                        "tf3": False,
                        "oprettet_af": {
                            "id": self.user.id,
                            "username": "payment-test-user",
                            "first_name": "",
                            "last_name": "",
                            "email": "",
                            "is_superuser": False,
                            "groups": [],
                            "permissions": [
                                "anmeldelse.add_afgiftsanmeldelse",
                                "anmeldelse.change_afgiftsanmeldelse",
                                "anmeldelse.view_afgiftsanmeldelse",
                                "anmeldelse.view_historicalafgiftsanmeldelse",
                            ],
                            "indberetter_data": {"cvr": 13371337},
                            "twofactor_enabled": False,
                        },
                        "oprettet_på_vegne_af": None,
                        "toldkategori": None,
                        "fuldmagtshaver": None,
                        "beregnet_faktureringsdato": Afgiftsanmeldelse.beregn_faktureringsdato(
                            self.afgiftsanmeldelse
                        ).isoformat(),
                        "history_username": None,
                        "history_date": ANY,
                    }
                ],
            },
        )

    def test_get_afgiftsanmeldelse_history_item(self):
        # Invoke the endpoint
        resp = self.client.get(
            reverse(
                "api-1.0.0:afgiftsanmeldelse_get_history_item",
                args=[self.afgiftsanmeldelse.id, 0],
            ),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            {
                "id": self.afgiftsanmeldelse.id,
                "afsender": {
                    "id": self.afsender.id,
                    "navn": "Testfirma 1",
                    "adresse": "Testvej 42",
                    "postnummer": 1234,
                    "by": "TestBy",
                    "postbox": "123",
                    "telefon": "123456",
                    "cvr": 12345678,
                    "kladde": False,
                    "stedkode": None,
                },
                "modtager": {
                    "id": self.modtager.id,
                    "navn": "Testfirma 1",
                    "adresse": "Testvej 42",
                    "postnummer": 1234,
                    "by": "TestBy",
                    "postbox": "123",
                    "telefon": "123456",
                    "cvr": 12345678,
                    "kreditordning": True,
                    "kladde": False,
                    "stedkode": None,
                },
                "fragtforsendelse": None,
                "postforsendelse": {
                    "id": self.postforsendelse.id,
                    "forsendelsestype": Postforsendelse.Forsendelsestype.SKIB,
                    "postforsendelsesnummer": "1234",
                    "afsenderbykode": "8200",
                    "afgangsdato": "2023-11-03",
                    "kladde": False,
                },
                "leverandørfaktura_nummer": "12345",
                "leverandørfaktura": "",
                "betales_af": "afsender",
                "indførselstilladelse": "abcde",
                "afgift_total": "0.00",
                "betalt": False,
                "dato": ANY,
                "status": "ny",
                "tf3": False,
                "oprettet_af": {
                    "id": self.user.id,
                    "username": "payment-test-user",
                    "first_name": "",
                    "last_name": "",
                    "email": "",
                    "is_superuser": False,
                    "groups": [],
                    "permissions": [
                        "anmeldelse.add_afgiftsanmeldelse",
                        "anmeldelse.change_afgiftsanmeldelse",
                        "anmeldelse.view_afgiftsanmeldelse",
                        "anmeldelse.view_historicalafgiftsanmeldelse",
                    ],
                    "indberetter_data": {"cvr": 13371337},
                    "twofactor_enabled": False,
                },
                "oprettet_på_vegne_af": None,
                "toldkategori": None,
                "fuldmagtshaver": None,
                "beregnet_faktureringsdato": Afgiftsanmeldelse.beregn_faktureringsdato(
                    self.afgiftsanmeldelse
                ).isoformat(),
                "history_username": None,
                "history_date": ANY,
            },
        )

    @patch("django.db.models.QuerySet.none")
    def test_list_filter_user_no_cvr(self, mock_queryset_none):
        user_private, user_private_token, _ = RestMixin.make_user(
            username="payment-test-user-private",
            plaintext_password="testpassword1337",
            permissions=[
                self.view_afgiftsanmeldelse_perm,
                self.add_afgiftsanmeldelse_perm,
                self.change_afgiftsanmeldelse_perm,
                self.view_historicalafgiftsanmeldelse,
            ],
        )

        _ = IndberetterProfile.objects.create(
            user=user_private,
            cpr="13371337",
            api_key=uuid4(),
        )

        resp = self.client.get(
            reverse(
                "api-1.0.0:afgiftsanmeldelse_list",
            ),
            HTTP_AUTHORIZATION=f"Bearer {user_private_token}",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        mock_queryset_none.assert_called_once()

    @patch("anmeldelse.api.AfgiftsanmeldelseAPI.check_user")
    def test_update_missing_approve_reject_anmeldelse_perm(self, mock_check_user):
        resp = self.client.patch(
            reverse(
                "api-1.0.0:afgiftsanmeldelse_update", args=[self.afgiftsanmeldelse.id]
            ),
            data=json_dump(
                {
                    "status": "godkendt",
                }
            ),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 403)

        # Verify the normal permission check was called, which we have mocked out
        # so we are sure its not the one raising PermissionDenied
        mock_check_user.assert_called_once_with(self.afgiftsanmeldelse)

    @patch("anmeldelse.api.AfgiftsanmeldelseAPI.check_user")
    def test_update_status_kladde(self, mock_check_user):
        postforsendelse_kladde, _ = Postforsendelse.objects.get_or_create(
            postforsendelsesnummer="1337",
            oprettet_af=self.user,
            defaults={
                "forsendelsestype": Postforsendelse.Forsendelsestype.SKIB,
                "afsenderbykode": "8200",
                "afgangsdato": "2024-05-06",
                "kladde": True,
            },
        )

        afgiftsanmeldelse_kladde = Afgiftsanmeldelse.objects.create(
            **{
                "afsender_id": self.afsender.id,
                "modtager_id": self.modtager.id,
                "postforsendelse_id": postforsendelse_kladde.id,
                "leverandørfaktura_nummer": "12345",
                "betales_af": "afsender",
                "indførselstilladelse": "abcde",
                "betalt": False,
                "fuldmagtshaver": None,
                "status": "kladde",
                "oprettet_af": self.user,
            }
        )

        resp = self.client.patch(
            reverse(
                "api-1.0.0:afgiftsanmeldelse_update", args=[afgiftsanmeldelse_kladde.id]
            ),
            data=json_dump(
                {
                    "leverandørfaktura_nummer": "54321",
                }
            ),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
        )

        mock_check_user.assert_called_once_with(afgiftsanmeldelse_kladde)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"success": True})

        # Verify the status was changed from "kladde" to "ny"
        afgiftsanmeldelse_kladde.refresh_from_db()
        self.assertEqual(afgiftsanmeldelse_kladde.status, "ny")

    @patch("anmeldelse.api.log.info")
    @patch("anmeldelse.api.AfgiftsanmeldelseAPI.check_user")
    def test_update_leverandoerfaktura_already_exists(
        self, mock_check_user, mock_log_info
    ):
        postforsendelse_kladde, _ = Postforsendelse.objects.get_or_create(
            postforsendelsesnummer="1338",
            oprettet_af=self.user,
            defaults={
                "forsendelsestype": Postforsendelse.Forsendelsestype.SKIB,
                "afsenderbykode": "8200",
                "afgangsdato": "2024-05-06",
                "kladde": False,
            },
        )

        afgiftsanmeldelse_kladde = Afgiftsanmeldelse.objects.create(
            **{
                "afsender_id": self.afsender.id,
                "modtager_id": self.modtager.id,
                "postforsendelse_id": postforsendelse_kladde.id,
                "leverandørfaktura": ContentFile(
                    "test_leverandoerfaktura_content",
                    name="test_leverandoerfaktura_content.txt",
                ),
                "leverandørfaktura_nummer": "12345",
                "betales_af": "afsender",
                "indførselstilladelse": "abcde",
                "betalt": False,
                "fuldmagtshaver": None,
                "status": "kladde",
                "oprettet_af": self.user,
            }
        )

        resp = self.client.patch(
            reverse(
                "api-1.0.0:afgiftsanmeldelse_update", args=[afgiftsanmeldelse_kladde.id]
            ),
            data=json_dump(
                {
                    "leverandørfaktura_nummer": "11223",
                }
            ),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"success": True})

        mock_check_user.assert_called_once_with(afgiftsanmeldelse_kladde)
        mock_log_info.assert_has_calls(
            [
                call(
                    "Rest API opdaterer TF10 %d uden at sætte leverandørfaktura",
                    afgiftsanmeldelse_kladde.id,
                ),
                call(
                    "Der findes allerede leverandørfaktura '%s' (%d bytes)",
                    afgiftsanmeldelse_kladde.leverandørfaktura.name,
                    afgiftsanmeldelse_kladde.leverandørfaktura.size,
                ),
            ]
        )

    def test_map_sort(self):
        result = AfgiftsanmeldelseAPI.map_sort("forbindelsesnummer", "desc")
        self.assertEqual(result, "-fragtforsendelse__forbindelsesnr")
