# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from aktør.models import Afsender, Modtager
from anmeldelse.models import Afgiftsanmeldelse, afgiftsanmeldelse_upload_to
from common.models import IndberetterProfile
from django.contrib.auth.models import Permission, User
from django.forms import model_to_dict
from django.test import TestCase
from django.urls import reverse
from forsendelse.models import Fragtforsendelse, Postforsendelse
from project.test_mixins import RestMixin, RestTestMixin
from project.util import json_dump


class PostforsendelseTest(RestTestMixin, TestCase):
    object_class = Postforsendelse
    unique_fields = []
    exclude_fields = ["oprettet_af"]
    has_delete = True

    def setUp(self) -> None:
        super().setUp()
        self.creation_data = self.postforsendelse_data

    # Expected object in the database as dict
    @property
    def expected_object_data(self):
        if not hasattr(self, "_expected_object_data"):
            self._expected_object_data = {}
            self._expected_object_data.update(self.strip_id(self.creation_data))
            self._expected_object_data.update(
                {
                    "id": self.postforsendelse.id,
                    "kladde": False,
                }
            )
        return self._expected_object_data

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

    # def test_kladde(self):
    #     self.creation_data = {"kladde": True}


class FragtforsendelseTest(RestTestMixin, TestCase):
    plural_classname = "fragtforsendelser"
    object_class = Fragtforsendelse
    unique_fields = []
    exclude_fields = ["oprettet_af"]
    has_delete = True

    def setUp(self) -> None:
        super().setUp()
        self.creation_data = self.fragtforsendelse_data

    # Expected object in the database as dict
    @property
    def expected_object_data(self):
        if not hasattr(self, "_expected_object_data"):
            self._expected_object_data = {}
            self._expected_object_data.update(self.strip_id(self.creation_data))
            self._expected_object_data.update(
                {
                    "id": self.fragtforsendelse.id,
                    "kladde": False,
                }
            )
        return self._expected_object_data

    def create_items(self):
        self.precreated_item = self.fragtforsendelse

    invalid_itemdata = {
        "forsendelsestype": [1234, 0, -1, "a", "Q"],
        "fragtbrevsnummer": ["123456789012345678901", "12345"],
        "fragtbrev": ["aaaa"],
        "forbindelsesnr": ["123", "abc"],
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
                    "fragtbrevsnummer": "ABCDE1234567",
                    "forbindelsesnr": "ABC 123",
                    "fragtbrev": self.fragtforsendelse_data["fragtbrev"],
                }
            )
        return self._update_object_data

    def test_str(self):
        string = str(self.fragtforsendelse)
        self.assertIn(self.fragtforsendelse_data["fragtbrevsnummer"], string)
        self.assertIn(str(self.fragtforsendelse_data["forsendelsestype"].label), string)
        self.assertIn(self.fragtforsendelse_data["forbindelsesnr"], string)


class PostforsendelseAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_permissions = [
            Permission.objects.get(codename="view_postforsendelse"),
            Permission.objects.get(codename="add_postforsendelse"),
        ]

        cls.user, cls.user_token, cls.user_refresh_token = RestMixin.make_user(
            username="payment-test-user",
            plaintext_password="testpassword1337",
            permissions=cls.user_permissions,
        )

    def test_create_postforsendelse_bad_request(self):
        resp = self.client.post(
            reverse("api-1.0.0:postforsendelse_create"),
            data=json_dump(
                {
                    "payload": {
                        "forsendelsestype": None,
                        "postforsendelsesnummer": None,
                        "afsenderbykode": None,
                        "afgangsdato": None,
                        "kladde": None,
                    }
                }
            ),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json(),
            {
                "__all__": [
                    "Begrænsning “aktuel_har_postforsendelsesnummer” er overtrådt.",
                    "Begrænsning “aktuel_har_afsenderbykode” er overtrådt.",
                ]
            },
        )

    def test_list_postforsendelser_filter_user_query_none(self):
        # Create some test data to list
        postforsendelse = Postforsendelse.objects.create(
            forsendelsestype=Postforsendelse.Forsendelsestype.SKIB,
            postforsendelsesnummer="1234567890",
            afsenderbykode="1234",
            afgangsdato="2023-01-01",
            kladde=False,
            oprettet_af=self.user,
        )

        resp = self.client.get(
            reverse("api-1.0.0:postforsendelse_list"),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"count": 0, "items": []})

    def test_list_postforsendelser_filter_user_created_by_indberetter_cvr(self):
        _ = IndberetterProfile.objects.create(
            user=self.user,
            cvr="13371337",
        )

        postforsendelse = Postforsendelse.objects.create(
            forsendelsestype=Postforsendelse.Forsendelsestype.SKIB,
            postforsendelsesnummer="1234567890",
            afsenderbykode="1234",
            afgangsdato="2023-01-01",
            kladde=False,
            oprettet_af=self.user,
        )

        _ = Afgiftsanmeldelse.objects.create(
            **{
                "status": "kladde",
                "leverandørfaktura_nummer": "12345",
                "betales_af": "afsender",
                "indførselstilladelse": "abcde",
                "betalt": False,
                "fuldmagtshaver": None,
                "oprettet_af": self.user,
                "postforsendelse": postforsendelse,
            }
        )

        resp = self.client.get(
            reverse("api-1.0.0:postforsendelse_list"),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            {
                "count": 1,
                "items": [
                    {
                        "id": postforsendelse.id,
                        "forsendelsestype": Postforsendelse.Forsendelsestype.SKIB[0],
                        "postforsendelsesnummer": postforsendelse.postforsendelsesnummer,
                        "afsenderbykode": postforsendelse.afsenderbykode,
                        "afgangsdato": postforsendelse.afgangsdato.isoformat(),
                        "kladde": postforsendelse.kladde,
                    }
                ],
            },
        )

    def test_get_postforsendelse_check_user_permission_denied(self):
        postforsendelse = Postforsendelse.objects.create(
            forsendelsestype=Postforsendelse.Forsendelsestype.SKIB,
            postforsendelsesnummer="1234567890",
            afsenderbykode="1234",
            afgangsdato="2023-01-01",
            kladde=False,
            oprettet_af=self.user,
        )

        resp = self.client.get(
            reverse("api-1.0.0:postforsendelse_get", args=[postforsendelse.id]),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(
            resp.json(),
            {
                "detail": "You do not have permission to perform this action.",
            },
        )
