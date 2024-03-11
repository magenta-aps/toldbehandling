# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from unittest.mock import ANY

from aktør.models import Afsender, Modtager
from anmeldelse.models import Afgiftsanmeldelse
from common.models import IndberetterProfile
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from forsendelse.models import Forsendelse, Fragtforsendelse, Postforsendelse
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


class FragtforsendelseAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_permissions = [
            Permission.objects.get(codename="add_fragtforsendelse"),
            Permission.objects.get(codename="change_fragtforsendelse"),
        ]

        cls.user, cls.user_token, cls.user_refresh_token = RestMixin.make_user(
            username="payment-test-user",
            plaintext_password="testpassword1337",
            permissions=cls.user_permissions,
        )

    def test_create_fragtforsendelse_draft(self):
        resp = self.client.post(
            reverse("api-1.0.0:fragtforsendelse_create"),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
            data=json_dump(
                {
                    "kladde": True,
                }
            ),
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"id": ANY})

    def test_create_fragtforsendelse_skib_bad_requests(self):
        resp_invalid_forbindelsesnr = self.client.post(
            reverse("api-1.0.0:fragtforsendelse_create"),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
            data=json_dump(
                {
                    "forsendelsestype": Forsendelse.Forsendelsestype.SKIB,
                    "fragtbrevsnummer": 12345678,
                    "forbindelsesnr": None,
                    "afgangsdato": "2024-12-31",
                    "kladde": False,
                }
            ),
        )

        self.assertEqual(resp_invalid_forbindelsesnr.status_code, 400)
        self.assertEqual(
            resp_invalid_forbindelsesnr.json(),
            {
                "__all__": [
                    "Ved skibsfragt skal forbindelsesnummer bestå af tre bogstaver, mellemrum og tre cifre",
                    "Begrænsning “aktuel_har_forbindelsesnr” er overtrådt.",
                ]
            },
        )
        # OBS: See `forsendelse/models.py::Fragtforsendelse.Meta.constraints` for the last error message

        resp_invalid_fragtbrevsnummer = self.client.post(
            reverse("api-1.0.0:fragtforsendelse_create"),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
            data=json_dump(
                {
                    "forsendelsestype": Forsendelse.Forsendelsestype.SKIB,
                    "fragtbrevsnummer": None,
                    "forbindelsesnr": "abc 123",
                    "afgangsdato": "2024-12-31",
                    "kladde": False,
                }
            ),
        )

        self.assertEqual(resp_invalid_fragtbrevsnummer.status_code, 400)
        self.assertEqual(
            resp_invalid_fragtbrevsnummer.json(),
            {
                "__all__": [
                    "Ved skibsfragt skal fragtbrevnr bestå af fem bogstaver efterfulgt af syv cifre",
                    "Begrænsning “aktuel_har_fragtbrevsnummer” er overtrådt.",
                ]
            },
        )
        # OBS: See `forsendelse/models.py::Fragtforsendelse.Meta.constraints` for the last error message

    def test_create_fragtforsendelse_fly_bad_requests(self):
        resp_invalid_forbindelsesnr = self.client.post(
            reverse("api-1.0.0:fragtforsendelse_create"),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
            data=json_dump(
                {
                    "forsendelsestype": Forsendelse.Forsendelsestype.FLY,
                    "fragtbrevsnummer": 12345678,
                    "forbindelsesnr": "abc",
                    "afgangsdato": "2024-12-31",
                    "kladde": False,
                }
            ),
        )

        self.assertEqual(resp_invalid_forbindelsesnr.status_code, 400)
        self.assertEqual(
            resp_invalid_forbindelsesnr.json(),
            {"__all__": ["Ved luftfragt skal forbindelsesnummer bestå af tre cifre"]},
        )

        resp_invalid_fragtbrevsnummer = self.client.post(
            reverse("api-1.0.0:fragtforsendelse_create"),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
            data=json_dump(
                {
                    "forsendelsestype": Forsendelse.Forsendelsestype.FLY,
                    "fragtbrevsnummer": 666,
                    "forbindelsesnr": "123",
                    "afgangsdato": "2024-12-31",
                    "kladde": False,
                }
            ),
        )

        self.assertEqual(resp_invalid_fragtbrevsnummer.status_code, 400)
        self.assertEqual(
            resp_invalid_fragtbrevsnummer.json(),
            {"__all__": ["Ved luftfragt skal fragtbrevnummer bestå af otte cifre"]},
        )

    def test_update_fragtforsendelse_created_by(self):
        _ = IndberetterProfile.objects.create(
            user=self.user,
            cvr="13371337",
        )

        fragtforsendelse = Fragtforsendelse.objects.create(
            forsendelsestype=Forsendelse.Forsendelsestype.SKIB,
            fragtbrevsnummer="abcde1234567",
            forbindelsesnr="abc 123",
            afgangsdato="2024-12-31",
            oprettet_af=self.user,
        )

        afsender = Afsender.objects.create(
            navn="Afsender1",
            adresse="Afsendervej 1",
            postnummer="1234",
            by="Afsenderby",
            postbox="1234",
            telefon="12345678",
            cvr="12345678",
            kladde=False,
        )

        modtager = Modtager.objects.create(
            navn="Modtager1",
            adresse="Modtagervej 1",
            postnummer="5678",
            by="Modtagerby",
            postbox="5678",
            telefon="87654321",
            cvr="87654321",
            kladde=False,
        )

        # Create test afgiftanmeldesel
        # OBS: Our permissions check method, FragtforsendelseAPI.checkUser(), requires an Afgiftsanmeldelse to exist
        # for the fragtforsendelse we want to update
        afgiftsanmeldelse = Afgiftsanmeldelse.objects.create(
            afsender=afsender,
            modtager=modtager,
            fragtforsendelse=Fragtforsendelse.objects.first(),
            postforsendelse=None,
            leverandørfaktura_nummer="1234",
            betales_af="afsender",
            indførselstilladelse="5678",
            betalt=False,
            oprettet_af=Fragtforsendelse.objects.first().oprettet_af,
        )

        # Invoke the endpoint
        resp = self.client.patch(
            reverse(
                "api-1.0.0:fragtforsendelse_update", kwargs={"id": fragtforsendelse.id}
            ),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
            data=json_dump(
                {
                    "forsendelsestype": Forsendelse.Forsendelsestype.SKIB,
                    "fragtbrevsnummer": "abcde1234567",
                    "forbindelsesnr": "abc 123",
                    "afgangsdato": "2024-12-31",
                    "kladde": False,
                }
            ),
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"success": True})

    def test_update_fragtforsendelse_indberetter_does_not_exist(self):
        fragtforsendelse = Fragtforsendelse.objects.create(
            forsendelsestype=Forsendelse.Forsendelsestype.SKIB,
            fragtbrevsnummer="abcde1234567",
            forbindelsesnr="abc 123",
            afgangsdato="2024-12-31",
            oprettet_af=self.user,
        )

        # Invoke the endpoint
        resp = self.client.patch(
            reverse(
                "api-1.0.0:fragtforsendelse_update", kwargs={"id": fragtforsendelse.id}
            ),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
            data=json_dump(
                {
                    "forsendelsestype": Forsendelse.Forsendelsestype.SKIB,
                    "fragtbrevsnummer": "abcde1234567",
                    "forbindelsesnr": "abc 123",
                    "afgangsdato": "2024-12-31",
                    "kladde": False,
                }
            ),
        )

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(
            resp.json(),
            {"detail": "You do not have permission to perform this action."},
        )
