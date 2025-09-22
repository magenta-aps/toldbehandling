# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

# Create your tests here.
import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from itertools import chain
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import unquote, urlencode

from aktør.models import Afsender, Modtager
from anmeldelse.models import Afgiftsanmeldelse, Varelinje
from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.files import File
from django.core.files.base import ContentFile
from django.db.models import Choices, Model
from django.db.models.fields.files import FieldFile
from django.test import Client
from django.urls import reverse
from forsendelse.models import Fragtforsendelse, Postforsendelse
from project.util import json_dump
from sats.models import Afgiftstabel, Vareafgiftssats


class RestMixin:
    invalid_itemdata = {}
    unique_fields = []
    exclude_fields = []
    has_delete = False
    object_restriction = False

    @classmethod
    def make_user(
        cls,
        username,
        plaintext_password,
        permissions: Union[List[Permission], None] = None,
        email: Optional[str] = None,
        is_staff: Optional[bool] = False,
        is_superuser: Optional[bool] = False,
    ) -> Tuple[User, str, str]:
        user = User.objects.create(
            username=username, is_staff=is_staff, is_superuser=is_superuser
        )
        user.email = email if email else user.email
        user.set_password(plaintext_password)
        user.save()

        if permissions is not None:
            user.user_permissions.set(permissions)
        else:
            user.user_permissions.clear()
        client = Client()
        response = client.post(
            "/api/token/pair",
            {"username": user.username, "password": plaintext_password},
            content_type="application/json",
        )
        data = response.json()
        return user, data["access"], data["refresh"]

    @classmethod
    def setUpClass(cls):
        super(RestMixin, cls).setUpClass()
        cls.leverandørfaktura_file = ContentFile(b"file_content")
        cls.fragtbrev_file = ContentFile(b"file_content")
        view_all_anmeldelser = Permission.objects.create(
            name="Kan se alle afgiftsanmeldelser, ikke kun egne",
            codename="view_all_anmeldelse",
            content_type=ContentType.objects.get_for_model(
                Afgiftsanmeldelse, for_concrete_model=False
            ),
        )
        view_approved_anmeldelser = Permission.objects.create(
            name="Kan se alle godkendte afgiftsanmeldelser",
            codename="view_approved_anmeldelse",
            content_type=ContentType.objects.get_for_model(
                Afgiftsanmeldelse, for_concrete_model=False
            ),
        )
        view_all_fragtforsendelser = Permission.objects.create(
            name="Kan se alle fragtforsendeler, ikke kun egne",
            codename="view_all_fragtforsendelser",
            content_type=ContentType.objects.get_for_model(
                Fragtforsendelse, for_concrete_model=False
            ),
        )
        view_all_postforsendelser = Permission.objects.create(
            name="Kan se alle postforsendelser, ikke kun egne",
            codename="view_all_postforsendelser",
            content_type=ContentType.objects.get_for_model(
                Postforsendelse, for_concrete_model=False
            ),
        )
        can_approve_reject_anmeldelse = Permission.objects.create(
            name="Kan godkende og afvise afgiftsanmeldelser",
            codename="approve_reject_anmeldelse",
            content_type=ContentType.objects.get_for_model(
                Afgiftsanmeldelse, for_concrete_model=False
            ),
        )
        permissions = [
            view_all_anmeldelser,
            view_all_fragtforsendelser,
            view_all_postforsendelser,
            can_approve_reject_anmeldelse,
        ]

        if hasattr(cls, "object_class"):
            permissions += [
                Permission.objects.get(
                    codename=f"{permission}_{cls.object_class.__name__.lower()}"
                )
                for permission in ("add", "change", "view", "delete")
            ]
        (
            cls.authorized_user,
            cls.authorized_access_token,
            authorized_refresh_token,
        ) = cls.make_user(
            "testuser1",
            "testpassword",
            permissions,
        )
        cls.authorized_user.user_permissions.add(
            Permission.objects.get(codename="view_all_anmeldelse")
        )

        (
            cls.staff_user,
            cls.staff_access_token,
            staff_refresh_token,
        ) = cls.make_user(
            "staffuser1",
            "staffpassword",
            permissions,
            is_staff=True,
        )
        cls.staff_user.user_permissions.add(
            Permission.objects.get(codename="view_all_anmeldelse")
        )

        permissions = [
            view_all_anmeldelser,
            view_all_fragtforsendelser,
            view_all_postforsendelser,
            can_approve_reject_anmeldelse,
        ]
        if hasattr(cls, "object_class"):
            permissions.append(
                Permission.objects.get(
                    codename=f"view_{cls.object_class.__name__.lower()}"
                )
            )
        (
            cls.viewonly_user,
            cls.viewonly_access_token,
            viewonly_refresh_token,
        ) = cls.make_user(
            "testuser2",
            "testpassword",
            permissions,
        )
        cls.viewonly_user.user_permissions.add(
            Permission.objects.get(codename="view_all_anmeldelse")
        )

        (
            cls.unauthorized_user,
            cls.unauthorized_access_token,
            unauthorized_refresh_token,
        ) = cls.make_user("testuser3", "testpassword", None)

        permissions = []
        if hasattr(cls, "object_class"):
            permissions.append(
                Permission.objects.get(
                    codename=f"view_{cls.object_class.__name__.lower()}"
                )
            )
        (
            cls.viewonly_own_user,
            cls.viewonly_own_access_token,
            viewonly_own_refresh_token,
        ) = cls.make_user(
            "testuser4",
            "testpassword",
            permissions,
        )  # udelad view_all

        (
            cls.approvedonly_user,
            cls.approvedonly_access_token,
            approvedonly_refresh_token,
        ) = cls.make_user(
            "testuser5",
            "testpassword",
            permissions,
        )
        for permission in [
            view_approved_anmeldelser,
            view_all_fragtforsendelser,
            view_all_postforsendelser,
        ]:
            cls.approvedonly_user.user_permissions.add(permission)

    def setUp(self) -> None:
        self.define_static_data()
        if not hasattr(self, "client"):
            self.client = Client()
        self.afgiftsanmeldelse_data["leverandørfaktura"] = self.leverandørfaktura_file
        self.fragtforsendelse_data["fragtbrev"] = self.fragtbrev_file

        # Override in subclasses
        self.calculated_fields = {}
        self.creation_data = {}

        super().setUp()

    # Expected object in the database as dict
    @property
    def expected_object_data(self):
        if not hasattr(self, "_expected_object_data"):
            self._expected_object_data = {}
            self._expected_object_data.update(self.strip_id(self.creation_data))
        return self._expected_object_data

    # Expected item from REST interface
    @property
    def expected_response_dict(self):
        return {**self.expected_object_data, **self.calculated_fields}

    def create_items(self):
        pass

    @property
    def sort_fields(self):
        return ()

    @classmethod
    def model_to_dict_forced(
        cls, instance: Model, fields=None, exclude=None
    ) -> Dict[str, Any]:
        """
        Same as django's model_to_dict, except we include non-editable fields
        """
        opts = instance._meta
        data = {}
        for f in chain(opts.concrete_fields, opts.private_fields, opts.many_to_many):
            if fields is not None and f.name not in fields:
                continue
            if exclude and f.name in exclude:
                continue
            data[f.name] = f.value_from_object(instance)
        return data

    @classmethod
    def traverse(cls, item, replacement_method=None):
        t = type(item)
        if t == dict:
            new = {}
            for key, value in item.items():
                new_value = cls.traverse(value)
                if callable(replacement_method):
                    new_value = replacement_method(new_value)
                new[key] = new_value
            return new
        return item

    @classmethod
    def object_to_dict(cls, item):
        def format_value(value):
            if type(value) in (date, datetime):
                return value.isoformat()
            if type(value) is FieldFile and not value:
                return None
            if type(value) is Decimal or isinstance(value, Choices):
                return str(value)
            return value

        return RestMixin.traverse(cls.model_to_dict_forced(item), format_value)

    @classmethod
    def filter_keys(cls, item: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
        if not keys:
            return item
        keyset = set(keys)
        return {key: value for key, value in item.items() if key not in keyset}

    @classmethod
    def get_file_data(cls, item) -> bytes:
        if isinstance(item, File):
            if item.closed:
                with item.open("rb") as fp:
                    return fp.read()
            else:
                item.seek(0)
                data = item.read()
                item.seek(0)
                return data
        if type(item) is str:
            path = os.path.normpath(settings.MEDIA_ROOT + "/" + unquote(item))
            with open(path, "rb") as fp:
                return fp.read()

    def compare_dicts(self, item1: dict, item2: dict, msg: str) -> None:
        filekeys = set()
        items_nofiles = [{}, {}]
        for i, item in enumerate([item1, item2]):
            for key, value in item.items():
                if isinstance(value, File):
                    filekeys.add(key)
                items_nofiles[i][key] = value
        for key in filekeys:
            file1 = self.get_file_data(items_nofiles[0].pop(key))
            file2 = self.get_file_data(items_nofiles[1].pop(key))
            self.assertEqual(file1, file2)
        msg = str(msg) + f" {str(items_nofiles[0])}\n != \n{str(items_nofiles[1])}"
        self.assertEquals(items_nofiles[0], items_nofiles[1], msg)

    def compare_in(self, itemlist: list, item: dict, msg: str) -> None:
        for expected in itemlist:
            try:
                self.compare_dicts(expected, item, msg)
            except AssertionError:
                continue
            return  # Loop until we find one that doesn't raise AssertionError
        raise AssertionError(msg + f" {itemlist}\n vs \n{item}")

    @classmethod
    def strip_id(cls, item: Dict[str, Any]) -> Dict[str, Any]:
        return {re.sub("_id$", "", key): value for key, value in item.items()}

    @classmethod
    def alter_value(cls, key: str, value: Any) -> Any:
        t = type(value)
        if t == str:
            try:
                d = date.fromisoformat(value)
                return (d + timedelta(days=200)).isoformat()
            except (TypeError, ValueError):
                pass
            try:
                d = Decimal(value)
                if str(d) == value:
                    return str(d + Decimal(17.5))
            except InvalidOperation:
                pass
            return f"{value}_nonexistent"
        if t == int:
            return value + 123456
        if t == bool:
            return not value

    @property
    def afsender(self) -> Afsender:
        if not hasattr(self, "_afsender"):
            try:
                self._afsender = Afsender.objects.get(navn=self.afsender_data["navn"])
            except Afsender.DoesNotExist:
                self._afsender = Afsender.objects.create(**self.afsender_data)
        return self._afsender

    @property
    def modtager(self) -> Modtager:
        if not hasattr(self, "_modtager"):
            try:
                self._modtager = Modtager.objects.get(navn=self.modtager_data["navn"])
            except Modtager.DoesNotExist:
                self._modtager = Modtager.objects.create(**self.modtager_data)
        return self._modtager

    @property
    def fragtforsendelse(self) -> Fragtforsendelse:
        if not hasattr(self, "_fragtforsendelse"):
            try:
                self._fragtforsendelse = Fragtforsendelse.objects.get(
                    fragtbrevsnummer=self.fragtforsendelse_data["fragtbrevsnummer"]
                )
            except Fragtforsendelse.DoesNotExist:
                self._fragtforsendelse = Fragtforsendelse.objects.create(
                    **self.fragtforsendelse_data,
                    oprettet_af=self.authorized_user,
                )
                self._fragtforsendelse.fragtbrev.save(
                    "fragtforsendelse.pdf", self.fragtforsendelse_data["fragtbrev"]
                )
        return self._fragtforsendelse

    @property
    def postforsendelse(self) -> Postforsendelse:
        if not hasattr(self, "_postforsendelse"):
            self._postforsendelse, _ = Postforsendelse.objects.get_or_create(
                postforsendelsesnummer=self.postforsendelse_data[
                    "postforsendelsesnummer"
                ],
                oprettet_af=self.authorized_user,
                defaults=self.postforsendelse_data,
            )
        return self._postforsendelse

    @property
    def afgiftsanmeldelse(self) -> Afgiftsanmeldelse:
        if not hasattr(self, "_afgiftsanmeldelse"):
            self._afgiftsanmeldelse = Afgiftsanmeldelse.objects.first()
            if self._afgiftsanmeldelse is None:
                data = {**self.afgiftsanmeldelse_data}
                data.update(
                    {
                        "afsender": self.afsender,
                        "modtager": self.modtager,
                        "fragtforsendelse": None,
                        "postforsendelse": self.postforsendelse,
                        "oprettet_af": self.authorized_user,
                    }
                )
                self._afgiftsanmeldelse = Afgiftsanmeldelse.objects.create(**data)

                faktura_id = self._afgiftsanmeldelse.pk
                media_path = f"../upload/leverandørfakturaer/{faktura_id}"
                try:
                    os.remove(os.path.join(media_path, "leverandørfaktura.pdf"))
                except FileNotFoundError:
                    pass

                self._afgiftsanmeldelse.leverandørfaktura.save(
                    "leverandørfaktura.pdf",
                    self.afgiftsanmeldelse_data["leverandørfaktura"],
                )

        return self._afgiftsanmeldelse

    @property
    def varelinje(self) -> Varelinje:
        if not hasattr(self, "_varelinje"):
            try:
                self._varelinje = Varelinje.objects.get(
                    vareafgiftssats=self.vareafgiftssats,
                    afgiftsanmeldelse=self.afgiftsanmeldelse,
                )
            except Varelinje.DoesNotExist:
                data = {**self.varelinje_data}
                data.update(
                    {
                        "vareafgiftssats": self.vareafgiftssats,
                        "afgiftsanmeldelse": self.afgiftsanmeldelse,
                    }
                )
                self._varelinje = Varelinje.objects.create(**data)
        return self._varelinje

    @property
    def vareafgiftssats(self) -> Vareafgiftssats:
        if not hasattr(self, "_vareafgiftssats"):
            try:
                self._vareafgiftssats = Vareafgiftssats.objects.get(
                    afgiftsgruppenummer=1234
                )
            except Vareafgiftssats.DoesNotExist:
                data = {**self.vareafgiftssats_data}
                data.update({"afgiftstabel": self.afgiftstabel})
                self._vareafgiftssats = Vareafgiftssats.objects.create(**data)
        return self._vareafgiftssats

    @property
    def afgiftstabel(self) -> Afgiftstabel:
        if not hasattr(self, "_afgiftstabel"):
            try:
                today = date.today()
                self._afgiftstabel = Afgiftstabel.objects.get(
                    gyldig_fra__year=today.year,
                    gyldig_fra__month=today.month,
                    gyldig_fra__day=today.day,
                )
            except Afgiftstabel.DoesNotExist:
                self._afgiftstabel = Afgiftstabel.objects.create(
                    **self.afgiftstabel_data
                )
        return self._afgiftstabel

    def define_static_data(self) -> None:
        self.afsender_data = {
            "navn": "Testfirma 1",
            "adresse": "Testvej 42",
            "postnummer": 1234,
            "by": "TestBy",
            "postbox": "123",
            "telefon": "123456",
            "cvr": 12345678,
            "kladde": False,
        }
        self.afsender_data_expected = {
            **self.afsender_data,
            "stedkode": None,
        }
        self.modtager_data = {
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
        self.modtager_data_expected = {
            **self.modtager_data,
            "stedkode": None,
        }

        self.fragtforsendelse_data = {
            "forsendelsestype": Fragtforsendelse.Forsendelsestype.SKIB,
            "fragtbrevsnummer": "ABCDE1234567",
            "forbindelsesnr": "ABC 123",
            "afgangsdato": "2023-11-03",
            "kladde": False,
        }
        self.postforsendelse_data = {
            "forsendelsestype": Postforsendelse.Forsendelsestype.SKIB,
            "postforsendelsesnummer": "1234",
            "afsenderbykode": "8200",
            "afgangsdato": "2023-11-03",
            "kladde": False,
        }
        self.afgiftsanmeldelse_data = {
            "leverandørfaktura_nummer": "12345",
            "betales_af": "afsender",
            "indførselstilladelse": "abcde",
            "betalt": False,
            "fuldmagtshaver": None,
        }
        self.varelinje_data = {
            "mængde": "15.000",
            "antal": 1,
            "fakturabeløb": "1000.00",
            "afgiftsbeløb": "37.50",
            "kladde": False,
        }
        self.vareafgiftssats_data = {
            "vareart_da": "Kaffe",
            "vareart_kl": "Kaffe",
            "afgiftsgruppenummer": 1234,
            "enhed": Vareafgiftssats.Enhed.KILOGRAM,
            "afgiftssats": "2.50",
            "kræver_indførselstilladelse": False,
            "har_privat_tillægsafgift_alkohol": False,
            "synlig_privat": False,
        }
        self.afgiftstabel_data = {"gyldig_fra": datetime.now(timezone.utc).isoformat()}

    @staticmethod
    def unenumerate(item):
        return {
            key: value.value if isinstance(value, Enum) else value
            for key, value in item.items()
        }


class RestTestMixin(RestMixin):
    @property
    def create_function(self) -> str:
        return f"{self.object_class.__name__.lower()}_create"

    @property
    def get_function(self) -> str:
        return f"{self.object_class.__name__.lower()}_get"

    @property
    def get_full_function(self) -> Union[str, None]:
        return None

    @property
    def list_function(self) -> str:
        return f"{self.object_class.__name__.lower()}_list"

    @property
    def list_full_function(self) -> Union[str, None]:
        return None

    @property
    def update_function(self) -> str:
        return f"{self.object_class.__name__.lower()}_update"

    @property
    def delete_function(self) -> str:
        return f"{self.object_class.__name__.lower()}_delete"

    def test_get_access(self):
        self.create_items()
        url = reverse(
            f"api-1.0.0:{self.get_function}", kwargs={"id": self.precreated_item.id}
        )
        response = self.client.get(
            url, HTTP_AUTHORIZATION=f"Bearer {self.authorized_access_token}"
        )
        self.assertEquals(response.status_code, 200)
        response = self.client.get(
            url, HTTP_AUTHORIZATION=f"Bearer {self.viewonly_access_token}"
        )
        self.assertEquals(response.status_code, 200)
        response = self.client.get(
            url, HTTP_AUTHORIZATION=f"Bearer {self.unauthorized_access_token}"
        )
        self.assertEquals(response.status_code, 403)
        if self.object_restriction:
            response = self.client.get(
                url, HTTP_AUTHORIZATION=f"Bearer {self.viewonly_own_access_token}"
            )
            self.assertEquals(response.status_code, 403)

    def test_get(self):
        self.create_items()
        url = reverse(
            f"api-1.0.0:{self.get_function}", kwargs={"id": self.precreated_item.id}
        )
        response = self.client.get(
            url, HTTP_AUTHORIZATION=f"Bearer {self.authorized_access_token}"
        )
        self.assertEqual(
            response.status_code,
            200,
            f"Reach READ API endpoint with existing id, expect HTTP 200 for GET {url}",
        )
        self.compare_dicts(
            {
                **self.filter_keys(
                    self.object_to_dict(self.precreated_item), self.exclude_fields
                ),
                **self.calculated_fields,
            },
            response.json(),
            f"Querying READ API endpoint, expected data to match for url {url}",
        )

    def test_get_404(self):
        self.create_items()
        url = reverse(
            f"api-1.0.0:{self.get_function}",
            kwargs={"id": self.object_class.objects.all().count()},
        )
        response = self.client.get(
            url, HTTP_AUTHORIZATION=f"Bearer {self.authorized_access_token}"
        )
        self.assertEqual(
            response.status_code,
            404,
            "Reach READ API endpoint with nonexisting id, expect HTTP 404"
            + f"for GET {url}. Got HTTP {response.status_code}: {response.content}",
        )

    def test_get_full(self):
        if self.get_full_function:
            self.create_items()
            url = reverse(
                f"api-1.0.0:{self.get_full_function}",
                kwargs={"id": self.precreated_item.id},
            )
            response = self.client.get(
                url, HTTP_AUTHORIZATION=f"Bearer {self.authorized_access_token}"
            )
            self.assertEqual(
                response.status_code,
                200,
                "Reach READ API endpoint with existing id, "
                f"expect HTTP 200 for GET {url}",
            )
            self.compare_dicts(
                response.json(),
                self.expected_full_object_data,
                f"Querying READ API endpoint, expected data to match for url {url}",
            )

    def test_list(self):
        self.create_items()
        for sort in [None] + list(self.sort_fields):
            for order in ("asc", "desc"):
                url = (
                    reverse(f"api-1.0.0:{self.list_function}")
                    + f"?sort={sort}&order={order}"
                )
                response = self.client.get(
                    url, HTTP_AUTHORIZATION=f"Bearer {self.authorized_access_token}"
                )
                self.assertEqual(
                    response.status_code,
                    200,
                    f"Reach LIST API endpoint, expect HTTP 200 for GET {url}. "
                    + f"Got HTTP {response.status_code}: {response.content}",
                )
                self.compare_in(
                    response.json()["items"],
                    self.expected_response_dict,
                    f"Querying LIST API endpoint, expected data to match for GET {url}",
                )

    def test_list_full(self):
        if self.list_full_function:
            self.create_items()
            url = reverse(f"api-1.0.0:{self.list_full_function}") + "?sort=id&order=asc"
            response = self.client.get(
                url, HTTP_AUTHORIZATION=f"Bearer {self.authorized_access_token}"
            )
            self.assertEqual(
                response.status_code,
                200,
                f"Reach LIST API endpoint, expect HTTP 200 for GET {url}. "
                + f"Got HTTP {response.status_code}: {response.content}",
            )
            self.compare_in(
                response.json()["items"],
                self.expected_list_full_response_dict,
                f"Querying LIST API endpoint, expected data to match for GET {url}",
            )

    def test_list_filter(self):
        self.create_items()
        for key, value in self.filter_data.items():
            if value is None:
                continue
            # attribute_model_class = getattr(self.object_class, key)
            # if isinstance(attribute_model_class, ForwardManyToOneDescriptor):
            #     key = f"{key}__id"
            url = (
                reverse(f"api-1.0.0:{self.list_function}")
                + "?"
                + urlencode({key: value})
            )
            response = self.client.get(
                url, HTTP_AUTHORIZATION=f"Bearer {self.authorized_access_token}"
            )
            self.assertEqual(
                response.status_code,
                200,
                "Reach LIST API endpoint with existing id, expect HTTP 200 or 201 "
                + f"for GET {url}. Got HTTP {response.status_code}: {response.content}",
            )
            self.compare_in(
                response.json()["items"],
                self.expected_response_dict,
                f"Querying LIST API endpoint, expected data to match for GET {url}",
            )

    @property
    def filter_data(self):
        return self.strip_id(self.creation_data)

    def test_list_filter_negative(self):
        self.create_items()
        for key, value in self.filter_data.items():
            if isinstance(value, File) or value is None:
                continue
            altered_value = self.alter_value(key, value)
            url = (
                reverse(f"api-1.0.0:{self.list_function}")
                + "?"
                + urlencode({key: altered_value})
            )
            response = self.client.get(
                url, HTTP_AUTHORIZATION=f"Bearer {self.authorized_access_token}"
            )
            self.assertEqual(
                response.status_code,
                200,
                "Reach LIST API endpoint with existing id, expected HTTP 200 or 201 "
                + f"for GET {url}. Got HTTP {response.status_code}: {response.content}",
            )
            self.assertNotIn(
                self.object_to_dict(self.precreated_item),
                response.json()["items"],
                f"Querying LIST API endpoint, expected data to not match for GET {url}",
            )

    def test_post_access(self):
        data = json_dump(self.creation_data)
        url = reverse(f"api-1.0.0:{self.create_function}")
        response = self.client.post(
            url,
            data,
            HTTP_AUTHORIZATION=f"Bearer {self.viewonly_access_token}",
            content_type="application/json",
        )
        self.assertEquals(response.status_code, 403)
        response = self.client.post(
            url,
            data,
            HTTP_AUTHORIZATION=f"Bearer {self.unauthorized_access_token}",
            content_type="application/json",
        )
        self.assertEquals(response.status_code, 403)
        response = self.client.post(
            url,
            data,
            HTTP_AUTHORIZATION=f"Bearer {self.authorized_access_token}",
            content_type="application/json",
        )
        self.assertEquals(response.status_code, 200)

    def test_create(self):
        url = reverse(f"api-1.0.0:{self.create_function}")

        # Hvis vi ønsker at overføre data med multipart/form-data, skal dette ændres til
        # response = self.client.post(
        #     url, self.creation_data, HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
        # )

        response = self.client.post(
            url,
            json_dump(self.creation_data),
            HTTP_AUTHORIZATION=f"Bearer {self.authorized_access_token}",
            content_type="application/json",
        )
        self.assertIn(
            response.status_code,
            (200, 201),
            f"Reach CREATE API endpoint, expect HTTP 200 or 201 for POST {url}.  "
            + f"Got HTTP {response.status_code}: {response.content}",
        )
        try:
            response_object = json.loads(response.content)
        except json.decoder.JSONDecodeError:
            raise AssertionError(
                f"Non-json response from POST {url}: {response.content}"
            )
        id = response_object["id"]
        try:
            item = self.object_class.objects.get(id=id)
        except self.object_class.DoesNotExist:
            raise AssertionError(
                f"Did not find created item {self.object_class.__name__}"
                + f"(id={id}) after creation with POST {url}"
            )
        item_dict = self.filter_keys(self.object_to_dict(item), self.exclude_fields)
        self.compare_dicts(
            item_dict,
            self.strip_id(self.expected_object_data),
            f"Created item {self.object_class.__name__}(id={id}) did not "
            + f"match expectation after creation with POST {url}",
        )

    def test_create_invalid(self):
        url = reverse(f"api-1.0.0:{self.create_function}")
        for key, values in self.invalid_itemdata.items():
            for value in values:
                invalid_data = {**self.creation_data, key: value}
                invalid_data = dict(
                    filter(lambda x: x[1] is not None, invalid_data.items())
                )
                response = self.client.post(
                    url,
                    invalid_data,
                    HTTP_AUTHORIZATION=f"Bearer {self.authorized_access_token}",
                )
                self.assertIn(
                    response.status_code,
                    (400, 422),
                    "Reach CREATE API endpoint with invalid data, expect HTTP "
                    + f"400 or 422 for POST {url} with data {invalid_data}. "
                    + f"Got HTTP {response.status_code}: {response.content}",
                )

    def test_create_unique(self):
        self.create_items()
        url = reverse(f"api-1.0.0:{self.create_function}")
        for field in self.unique_fields:
            invalid_data = json_dump(
                {
                    **self.creation_data,
                    field: getattr(self.precreated_item, field),
                }
            )
            response = self.client.post(
                url,
                invalid_data,
                HTTP_AUTHORIZATION=f"Bearer {self.authorized_access_token}",
                content_type="application/json",
            )
            self.assertEqual(
                response.status_code,
                400,
                "Reach CREATE API endpoint with data that collides with "
                + f"existing object, expected HTTP 400 for POST {url} with data "
                + f"{invalid_data}. Got {response.status_code}: {response.content}",
            )

    def test_patch_access(self):
        self.create_items()
        data = json_dump(self.update_object_data)
        url = reverse(
            f"api-1.0.0:{self.update_function}", kwargs={"id": self.precreated_item.id}
        )
        response = self.client.patch(
            url,
            data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.unauthorized_access_token}",
        )
        self.assertEquals(response.status_code, 403)
        response = self.client.patch(
            url,
            data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.viewonly_access_token}",
        )
        self.assertEquals(response.status_code, 403)
        response = self.client.patch(
            url,
            data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.authorized_access_token}",
        )
        self.assertEquals(response.status_code, 200)

    def test_update(self):
        self.create_items()
        expected_object_data = self.strip_id(self.object_to_dict(self.precreated_item))
        url = reverse(
            f"api-1.0.0:{self.update_function}", kwargs={"id": self.precreated_item.id}
        )
        response = self.client.patch(
            url,
            json_dump(self.update_object_data),
            content_type="application/json",
            secure=False,
            HTTP_AUTHORIZATION=f"Bearer {self.authorized_access_token}",
        )
        self.assertIn(
            response.status_code,
            (200, 201),
            f"Reach UPDATE API endpoint, expected HTTP 200 or 201 for PATCH {url}",
        )
        self.precreated_item.refresh_from_db()
        item_dict = self.object_to_dict(self.precreated_item)
        expected_object_data.update(
            {"id": id, **self.strip_id(self.update_object_data)}
        )
        self.compare_dicts(
            item_dict,
            expected_object_data,
            f"Updated item {self.object_class.__name__}(id={id}) did not match "
            + f"expectation after updating with PATCH {url}",
        )

    def test_delete(self):
        if self.has_delete:
            self.create_items()
            url = reverse(f"api-1.0.0:{self.delete_function}", kwargs={"id": 10000})
            response = self.client.delete(
                url,
                secure=False,
                HTTP_AUTHORIZATION=f"Bearer {self.authorized_access_token}",
            )
            self.assertEquals(response.status_code, 404)

            url = reverse(
                f"api-1.0.0:{self.delete_function}",
                kwargs={"id": self.precreated_item.id},
            )
            response = self.client.delete(
                url,
                secure=False,
                HTTP_AUTHORIZATION=f"Bearer {self.authorized_access_token}",
            )
            self.assertEquals(response.status_code, 200)
