# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
import base64
import json
from collections import defaultdict
from typing import List, Tuple
from unittest.mock import patch
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile, TemporaryUploadedFile
from django.shortcuts import redirect
from django.test import TestCase, override_settings
from django.urls import reverse
from requests import Response
from told_common.data import Vareafgiftssats
from told_common.forms import TF5Form, TF10Form, TF10VareForm
from told_common.rest_client import RestClient
from told_common.tests import (
    AnmeldelseListViewTest,
    FileViewTest,
    HasLogin,
    TemplateTagsTest,
    TestMixin,
)


class TF10BlanketTest(TestMixin, HasLogin, TestCase):
    @property
    def login_url(self):
        return str(reverse("login:login"))

    formdata1 = {
        "afsender_cvr": "12345678",
        "afsender_navn": "TestFirma1",
        "afsender_adresse": "Testvej 42",
        "afsender_postnummer": "1234",
        "afsender_by": "TestBy",
        "afsender_postbox": "123",
        "afsender_telefon": "123456",
        "afsender_change_existing": "false",
        "modtager_cvr": "12345679",
        "modtager_navn": "TestFirma2",
        "modtager_adresse": "Testvej 43",
        "modtager_postnummer": "1234",
        "modtager_by": "TestBy",
        "modtager_postbox": "124",
        "modtager_telefon": "123123",
        "modtager_change_existing": "false",
        "indførselstilladelse": "123",
        "leverandørfaktura_nummer": "123",
        "fragttype": "skibsfragt",
        "fragtbrevnr": "123",
        "afgangsdato": "2023-11-03",
        "form-TOTAL_FORMS": "1",
        "form-INITIAL_FORMS": "1",
        "form-0-vareafgiftssats": "1",
        "form-0-mængde": "3",
        "form-0-antal": "6",
        "form-0-fakturabeløb": "100.00",
        "forbindelsesnr": "1337",
    }
    formdata2 = {**formdata1, "fragttype": "luftpost"}

    _formfiles1 = {
        "fragtbrev": SimpleUploadedFile("fragtbrev.txt", "Testtekst".encode("utf-8")),
        "leverandørfaktura": SimpleUploadedFile(
            "leverandørfaktura.txt", "Testtekst".encode("utf-8")
        ),
    }
    _formfiles2 = {
        "leverandørfaktura": SimpleUploadedFile(
            "leverandørfaktura.txt", "Testtekst".encode("utf-8")
        ),
    }
    subformdata1 = {
        "vareafgiftssats": "1",
        "mængde": "3",
        "antal": "6",
        "fakturabeløb": "100,00",
    }

    @property
    def formfiles1(self):
        for file in self._formfiles1.values():
            file.seek(0)
        return self._formfiles1

    @property
    def formfiles2(self):
        for file in self._formfiles2.values():
            file.seek(0)
        return self._formfiles2

    def setUp(self):
        super().setUp()
        self.posted: List[Tuple[str, str]] = []
        self.mock_existing = {
            "afsender": False,
            "modtager": False,
            "vareafgiftssats": True,
        }

    def test_uploadfile_to_base64str(self):
        file = TemporaryUploadedFile("testfile", "text/plain", 8, "utf-8")
        with file.open("+") as fp:
            fp.write(b"testdata")
            file.seek(0)
            self.assertEquals(RestClient._uploadfile_to_base64str(file), "dGVzdGRhdGE=")
        file = SimpleUploadedFile("testfile", b"testdata", "text/plain")
        file.seek(0)
        self.assertEquals(RestClient._uploadfile_to_base64str(file), "dGVzdGRhdGE=")

    @override_settings(LOGIN_BYPASS_ENABLED=False)
    def test_requires_login(self):
        url = str(reverse("tf10_create"))
        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)
        self.assertEquals(
            response.headers["Location"],
            reverse("login:login") + "?back=" + quote(url, safe=""),
        )

    def mock_requests_get(self, path):
        expected_prefix = f"{settings.REST_DOMAIN}/api/"
        path = path.split("?")[0]
        path = path.rstrip("/")
        response = Response()
        json_content = None
        content = None
        status_code = None
        empty = {"count": 0, "items": []}
        if path == expected_prefix + "afgiftstabel":
            json_content = {
                "count": 1,
                "items": [
                    {
                        "id": 1,
                        "gyldig_fra": "2023-01-01",
                        "gyldig_til": None,
                        "kladde": False,
                    }
                ],
            }
        elif path == expected_prefix + "vareafgiftssats":
            if self.mock_existing["vareafgiftssats"]:
                json_content = {
                    "count": 1,
                    "items": [
                        {
                            "id": 1,
                            "afgiftstabel": 1,
                            "vareart_da": "Båthorn",
                            "vareart_kl": "Båthorn",
                            "afgiftsgruppenummer": 1234567,
                            "enhed": "kg",
                            "afgiftssats": "1.00",
                            "kræver_indførselstilladelse": False,
                            "har_privat_tillægsafgift_alkohol": False,
                        }
                    ],
                }
            else:
                json_content = empty
        elif path == expected_prefix + "afsender":
            if self.mock_existing["afsender"]:
                json_content = {
                    "count": 1,
                    "items": [
                        {
                            "id": 1,
                            "navn": "Testfirma 1",
                            "adresse": "Testvej 42",
                            "postnummer": 1234,
                            "by": "TestBy",
                            "postbox": "123",
                            "telefon": "123456",
                            "cvr": 12345678,
                        }
                    ],
                }
            else:
                json_content = empty
        elif path == expected_prefix + "modtager":
            if self.mock_existing["modtager"]:
                json_content = {
                    "count": 1,
                    "items": [
                        {
                            "id": 1,
                            "navn": "Testfirma 1",
                            "adresse": "Testvej 42",
                            "postnummer": 1234,
                            "by": "TestBy",
                            "postbox": "123",
                            "telefon": "123456",
                            "cvr": 12345678,
                            "kreditordning": True,
                        }
                    ],
                }
            else:
                json_content = empty
        else:
            print(f"Mock got unrecognized path: {path}")
        if json_content:
            content = json.dumps(json_content).encode("utf-8")
        if content:
            if not status_code:
                status_code = 200
            response._content = content
        response.status_code = status_code or 404
        return response

    def mock_requests_post(self, path, data, headers=None):
        expected_prefix = f"{settings.REST_DOMAIN}/api/"
        path = path.rstrip("/")
        response = Response()
        json_content = None
        content = None
        status_code = None
        self.posted.append((path, data))
        if path in (
            expected_prefix + x
            for x in (
                "afsender",
                "modtager",
                "fragtforsendelse",
                "postforsendelse",
                "afgiftsanmeldelse",
                "varelinje",
            )
        ):
            json_content = {"id": 1}
        if json_content:
            content = json.dumps(json_content).encode("utf-8")
        if content:
            if not status_code:
                status_code = 200
            response._content = content
        response.status_code = status_code or 404
        return response

    def submit_get_errors(self, url, data):
        return self.get_errors(self.client.post(url, data=data).content)

    @patch.object(requests.Session, "get")
    def test_get_form(self, mock_get):
        self.login()
        url = reverse("tf10_create")
        mock_get.side_effect = self.mock_requests_get
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        soup = BeautifulSoup(response.content, "html.parser")
        input_field_names = set(
            [
                input_field["name"]
                for input_field in soup.find_all(name=["input", "select"])
                if input_field.has_attr("name")
            ]
        )
        for field_name in (
            "csrfmiddlewaretoken",
            "afsender_cvr",
            "afsender_navn",
            "afsender_adresse",
            "afsender_postnummer",
            "afsender_by",
            "afsender_postbox",
            "afsender_telefon",
            "modtager_cvr",
            "modtager_navn",
            "modtager_adresse",
            "modtager_postnummer",
            "modtager_by",
            "modtager_postbox",
            "modtager_telefon",
            "indførselstilladelse",
            "fragttype",
            "forbindelsesnr",
            "fragtbrevnr",
            "leverandørfaktura",
            "leverandørfaktura_nummer",
            "fragtbrev",
            "afgangsdato",
            "form-0-vareafgiftssats",
            "form-0-antal",
            "form-0-mængde",
            "form-0-fakturabeløb",
            "form-INITIAL_FORMS",
            "form-TOTAL_FORMS",
            "form-MIN_NUM_FORMS",
            "form-MAX_NUM_FORMS",
        ):
            self.assertIn(field_name, input_field_names, f"Missing {field_name}")

    @patch.object(requests.Session, "get")
    @patch("ui.views.TF10FormCreateView.form_valid")
    def test_form_required_fields(self, mock_form_valid, mock_get):
        self.login()
        url = reverse("tf10_create")
        mock_get.side_effect = self.mock_requests_get
        mock_form_valid.return_value = redirect(url)
        for required_field in (
            "afsender_navn",
            "modtager_navn",
        ):
            data = {**self.formdata1}
            del data[required_field]
            form = TF10Form(data=data, files=self.formfiles1)
            self.assertTrue(required_field in form.errors)
            self.assertEquals(form.errors[required_field], ["Dette felt er påkrævet."])
            html_errors = self.submit_get_errors(url, data)
            self.assertTrue(required_field in html_errors)
            self.assertEquals(html_errors[required_field], ["Dette felt er påkrævet."])

        files = {**self.formfiles1}
        del files["leverandørfaktura"]
        form = TF10Form(data=self.formdata1, files=files)
        self.assertEquals(form.errors["leverandørfaktura"], ["Dette felt er påkrævet."])
        html_errors = self.submit_get_errors(url, {**self.formdata1, **files})
        self.assertEquals(html_errors["leverandørfaktura"], ["Dette felt er påkrævet."])

    def test_vareform_required_fields(self):
        varesatser = {
            1: Vareafgiftssats(
                id=1,
                afgiftstabel=1,
                vareart_da="Båthorn",
                vareart_kl="Båthorn",
                afgiftsgruppenummer=12345678,
                enhed=Vareafgiftssats.Enhed.KILOGRAM,
                afgiftssats="1.00",
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            ),
            2: Vareafgiftssats(
                id=2,
                afgiftstabel=1,
                vareart_da="Klovnesko",
                vareart_kl="Klovnesko",
                afgiftsgruppenummer=87654321,
                enhed=Vareafgiftssats.Enhed.ANTAL,
                afgiftssats="1.00",
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            ),
            3: Vareafgiftssats(
                id=3,
                afgiftstabel=1,
                vareart_da="Ethjulede cykler",
                vareart_kl="Ethjulede cykler",
                afgiftsgruppenummer=22446688,
                enhed=Vareafgiftssats.Enhed.PROCENT,
                afgiftssats="0.50",
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            ),
        }

        for required_field in ("vareafgiftssats",):
            data = {**self.subformdata1}
            del data[required_field]
            form = TF10VareForm(data=data, varesatser=varesatser)
            self.assertTrue(required_field in form.errors)
            self.assertEquals(form.errors[required_field], ["Dette felt er påkrævet."])

        for required_field, vareart in (
            ("mængde", 1),
            ("antal", 2),
            ("fakturabeløb", 3),
        ):
            data = {**self.subformdata1, "vareafgiftssats": vareart}
            del data[required_field]
            form = TF10VareForm(data=data, varesatser=varesatser)
            self.assertTrue(required_field in form.errors, required_field)
            self.assertEquals(
                form.errors[required_field], ["Dette felt er påkrævet."], required_field
            )

    @patch.object(requests.Session, "get")
    @patch.object(
        requests.Session,
        "post",
    )
    def test_form_successful(self, mock_post, mock_get):
        self.login()
        url = reverse("tf10_create")
        mock_get.side_effect = self.mock_requests_get
        mock_post.side_effect = self.mock_requests_post
        response = self.client.post(url, data={**self.formdata1, **self.formfiles1})
        self.assertEquals(response.status_code, 302)
        prefix = f"{settings.REST_DOMAIN}/api/"
        posted_map = defaultdict(list)
        for url, data in self.posted:
            posted_map[url].append(json.loads(data))
        self.assertEquals(
            posted_map[prefix + "afsender"],
            [
                {
                    "navn": "TestFirma1",
                    "adresse": "Testvej 42",
                    "postnummer": 1234,
                    "by": "TestBy",
                    "postbox": "123",
                    "telefon": "123456",
                    "cvr": 12345678,
                    "kladde": False,
                }
            ],
        )
        self.assertEquals(
            posted_map[prefix + "modtager"],
            [
                {
                    "navn": "TestFirma2",
                    "adresse": "Testvej 43",
                    "postnummer": 1234,
                    "by": "TestBy",
                    "postbox": "124",
                    "telefon": "123123",
                    "cvr": 12345679,
                    "kladde": False,
                }
            ],
        )
        self.assertEquals(
            posted_map[prefix + "fragtforsendelse"],
            [
                {
                    "fragtbrevsnummer": "123",
                    "forsendelsestype": "S",
                    "forbindelsesnr": "1337",
                    "fragtbrev": base64.b64encode("Testtekst".encode("utf-8")).decode(
                        "ascii"
                    ),
                    "fragtbrev_navn": "fragtbrev.txt",
                    "afgangsdato": "2023-11-03",
                }
            ],
        )
        self.assertEquals(
            posted_map[prefix + "afgiftsanmeldelse"],
            [
                {
                    "leverandørfaktura_nummer": "123",
                    "indførselstilladelse": "123",
                    "afsender_id": 1,
                    "modtager_id": 1,
                    "postforsendelse_id": None,
                    "fragtforsendelse_id": 1,
                    "leverandørfaktura": base64.b64encode(
                        "Testtekst".encode("utf-8")
                    ).decode("ascii"),
                    "leverandørfaktura_navn": "leverandørfaktura.txt",
                    "modtager_betaler": False,
                    "oprettet_på_vegne_af_id": None,
                    "toldkategori": None,
                    "kladde": False,
                }
            ],
        )

    @patch.object(requests.Session, "get")
    @patch.object(
        requests.Session,
        "post",
    )
    def test_form_successful_preexisting_actors(self, mock_post, mock_get):
        self.mock_existing["afsender"] = True
        self.mock_existing["modtager"] = True
        self.login()
        url = reverse("tf10_create")
        mock_get.side_effect = self.mock_requests_get
        mock_post.side_effect = self.mock_requests_post
        response = self.client.post(url, data={**self.formdata1, **self.formfiles1})
        self.assertEquals(response.status_code, 302)
        prefix = f"{settings.REST_DOMAIN}/api/"
        posted_map = defaultdict(list)
        for url, data in self.posted:
            posted_map[url].append(json.loads(data))
        self.assertEquals(
            posted_map[prefix + "afsender"],
            [],
        )
        self.assertEquals(
            posted_map[prefix + "modtager"],
            [],
        )
        self.assertEquals(
            posted_map[prefix + "fragtforsendelse"],
            [
                {
                    "fragtbrevsnummer": "123",
                    "forbindelsesnr": "1337",
                    "forsendelsestype": "S",
                    "fragtbrev": base64.b64encode("Testtekst".encode("utf-8")).decode(
                        "ascii"
                    ),
                    "fragtbrev_navn": "fragtbrev.txt",
                    "afgangsdato": "2023-11-03",
                }
            ],
        )
        self.assertEquals(
            posted_map[prefix + "afgiftsanmeldelse"],
            [
                {
                    "leverandørfaktura_nummer": "123",
                    "indførselstilladelse": "123",
                    "afsender_id": 1,
                    "modtager_id": 1,
                    "postforsendelse_id": None,
                    "fragtforsendelse_id": 1,
                    "leverandørfaktura": base64.b64encode(
                        "Testtekst".encode("utf-8")
                    ).decode("ascii"),
                    "leverandørfaktura_navn": "leverandørfaktura.txt",
                    "modtager_betaler": False,
                    "oprettet_på_vegne_af_id": None,
                    "toldkategori": None,
                    "kladde": False,
                }
            ],
        )

    @patch.object(requests.Session, "get")
    @patch.object(
        requests.Session,
        "post",
    )
    def test_form_successful_postforsendelse(self, mock_post, mock_get):
        self.login()
        url = reverse("tf10_create")
        mock_get.side_effect = self.mock_requests_get
        mock_post.side_effect = self.mock_requests_post
        response = self.client.post(url, data={**self.formdata2, **self.formfiles2})
        self.assertEquals(response.status_code, 302)
        prefix = f"{settings.REST_DOMAIN}/api/"
        posted_map = defaultdict(list)
        for url, data in self.posted:
            posted_map[url].append(json.loads(data))
        self.assertEquals(
            posted_map[prefix + "afsender"],
            [
                {
                    "navn": "TestFirma1",
                    "adresse": "Testvej 42",
                    "postnummer": 1234,
                    "by": "TestBy",
                    "postbox": "123",
                    "telefon": "123456",
                    "cvr": 12345678,
                    "kladde": False,
                }
            ],
        )
        self.assertEquals(
            posted_map[prefix + "modtager"],
            [
                {
                    "navn": "TestFirma2",
                    "adresse": "Testvej 43",
                    "postnummer": 1234,
                    "by": "TestBy",
                    "postbox": "124",
                    "telefon": "123123",
                    "cvr": 12345679,
                    "kladde": False,
                }
            ],
        )
        self.assertEquals(
            posted_map[prefix + "postforsendelse"],
            [
                {
                    "postforsendelsesnummer": "123",
                    "forsendelsestype": "F",
                    "afsenderbykode": "1337",
                    "afgangsdato": "2023-11-03",
                }
            ],
        )
        self.assertEquals(
            posted_map[prefix + "afgiftsanmeldelse"],
            [
                {
                    "leverandørfaktura_nummer": "123",
                    "indførselstilladelse": "123",
                    "afsender_id": 1,
                    "modtager_id": 1,
                    "postforsendelse_id": 1,
                    "fragtforsendelse_id": None,
                    "leverandørfaktura": base64.b64encode(
                        "Testtekst".encode("utf-8")
                    ).decode("ascii"),
                    "leverandørfaktura_navn": "leverandørfaktura.txt",
                    "modtager_betaler": False,
                    "oprettet_på_vegne_af_id": None,
                    "toldkategori": None,
                    "kladde": False,
                }
            ],
        )

    @patch.object(requests.Session, "get")
    @patch("ui.views.TF10FormCreateView.form_valid")
    def test_form_filefields_size(self, mock_form_valid, mock_get):
        self.login()
        url = reverse("tf10_create")
        mock_get.side_effect = self.mock_requests_get
        mock_form_valid.return_value = redirect(url)
        data = {**self.formdata1}
        files = {
            "fragtbrev": SimpleUploadedFile("fragtbrev.txt", b"\x00" * 11000000),
            "leverandørfaktura": SimpleUploadedFile(
                "leverandørfaktura.txt", b"\x00" * 11000000
            ),
        }
        for v in files.values():
            v.seek(0)
        form = TF10Form(data=data, files=files)
        html_errors = self.submit_get_errors(url, {**data, **files})
        for file_field in (
            "leverandørfaktura",
            "fragtbrev",
        ):
            self.assertTrue(file_field in form.errors)
            self.assertEquals(
                form.errors[file_field], ["Filen er for stor; den må max. være 10.0 MB"]
            )
            self.assertTrue(file_field in html_errors)
            self.assertEquals(
                html_errors[file_field], ["Filen er for stor; den må max. være 10.0 MB"]
            )


class UiTemplateTagsTest(TemplateTagsTest, TestCase):
    pass


class UiAnmeldelseListViewTest(AnmeldelseListViewTest, TestCase):
    can_view = True
    can_edit = True

    @property
    def login_url(self):
        return str(reverse("login:login"))

    @property
    def list_url(self):
        return str(reverse("tf10_list"))

    def edit_url(self, id):
        return str(reverse("tf10_edit", kwargs={"id": id}))

    def view_url(self, id):
        return str(reverse("tf10_view", kwargs={"id": id}))


class UiFileViewTest(FileViewTest, TestCase):
    @property
    def login_url(self):
        return str(reverse("login:login"))

    @property
    def file_view_url(self):
        return str(reverse("fragtbrev_view", kwargs={"id": 1}))


class TF5BlanketTest(TestMixin, HasLogin, TestCase):
    @property
    def login_url(self):
        return str(reverse("login:login"))

    formdata1 = {
        "cpr": "1234567890",
        "navn": "TestPerson1",
        "adresse": "Testvej 42",
        "postnummer": "1234",
        "by": "TestBy",
        "telefon": "123456",
        "bookingnummer": "123",
        "indførselstilladelse": "123",
        "leverandørfaktura_nummer": "123",
        "indleveringsdato": "2023-11-03",
        "form-TOTAL_FORMS": "1",
        "form-INITIAL_FORMS": "1",
        "form-0-vareafgiftssats": "1",
        "form-0-mængde": "3",
        "form-0-antal": "6",
        "form-0-fakturabeløb": "100.00",
    }

    _formfiles1 = {
        "leverandørfaktura": SimpleUploadedFile(
            "leverandørfaktura.txt", "Testtekst".encode("utf-8")
        ),
    }
    subformdata1 = {
        "vareafgiftssats": "1",
        "mængde": "3",
        "antal": "6",
        "fakturabeløb": "100,00",
    }

    @property
    def formfiles1(self):
        for file in self._formfiles1.values():
            file.seek(0)
        return self._formfiles1

    def setUp(self):
        super().setUp()
        self.posted: List[Tuple[str, str]] = []

    @override_settings(LOGIN_BYPASS_ENABLED=False)
    def test_requires_login(self):
        if not settings.TF5_ENABLED:
            return
        url = str(reverse("tf5_create"))
        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)
        self.assertEquals(
            response.headers["Location"],
            reverse("login:login") + "?back=" + quote(url, safe=""),
        )

    def mock_requests_get(self, path):
        expected_prefix = f"{settings.REST_DOMAIN}/api/"
        path = path.split("?")[0]
        path = path.rstrip("/")
        response = Response()
        json_content = None
        content = None
        status_code = None
        empty = {"count": 0, "items": []}
        if path == expected_prefix + "afgiftstabel":
            json_content = {
                "count": 1,
                "items": [
                    {
                        "id": 1,
                        "gyldig_fra": "2023-01-01T00:00:00-03:00",
                        "gyldig_til": None,
                        "kladde": False,
                    }
                ],
            }
        elif path == expected_prefix + "vareafgiftssats":
            json_content = {
                "count": 1,
                "items": [
                    {
                        "id": 1,
                        "afgiftstabel": 1,
                        "vareart_da": "Båthorn",
                        "vareart_kl": "Båthorn",
                        "afgiftsgruppenummer": 1234567,
                        "enhed": "kg",
                        "afgiftssats": "1.00",
                        "kræver_indførselstilladelse": False,
                        "har_privat_tillægsafgift_alkohol": False,
                    }
                ],
            }
        else:
            print(f"Mock got unrecognized path: {path}")
        if json_content:
            content = json.dumps(json_content).encode("utf-8")
        if content:
            if not status_code:
                status_code = 200
            response._content = content
        response.status_code = status_code or 404
        return response

    def mock_requests_post(self, path, data, headers=None):
        expected_prefix = f"{settings.REST_DOMAIN}/api/"
        path = path.rstrip("/")
        response = Response()
        json_content = None
        content = None
        status_code = None
        self.posted.append((path, data))
        if path in (
            expected_prefix + x
            for x in (
                "privat_afgiftsanmeldelse",
                "varelinje",
            )
        ):
            json_content = {"id": 1}
        else:
            print(f"Mock got unrecognized path: {path}")
        if json_content:
            content = json.dumps(json_content).encode("utf-8")
        if content:
            if not status_code:
                status_code = 200
            response._content = content
        response.status_code = status_code or 404
        return response

    def submit_get_errors(self, url, data):
        return self.get_errors(self.client.post(url, data=data).content)

    @patch.object(requests.Session, "get")
    def test_get_form(self, mock_get):
        if not settings.TF5_ENABLED:
            return
        self.login()
        url = reverse("tf5_create")
        mock_get.side_effect = self.mock_requests_get
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        soup = BeautifulSoup(response.content, "html.parser")
        input_field_names = set(
            [
                input_field["name"]
                for input_field in soup.find_all(name=["input", "select"])
                if input_field.has_attr("name")
            ]
        )
        for field_name in (
            "csrfmiddlewaretoken",
            "cpr",
            "navn",
            "adresse",
            "postnummer",
            "by",
            "telefon",
            "bookingnummer",
            "leverandørfaktura",
            "leverandørfaktura_nummer",
            "indleveringsdato",
            "form-0-vareafgiftssats",
            "form-0-antal",
            "form-0-mængde",
            "form-0-fakturabeløb",
            "form-INITIAL_FORMS",
            "form-TOTAL_FORMS",
            "form-MIN_NUM_FORMS",
            "form-MAX_NUM_FORMS",
        ):
            self.assertIn(field_name, input_field_names, f"Missing {field_name}")

    @patch.object(requests.Session, "get")
    @patch("ui.views.TF5FormCreateView.form_valid")
    def test_form_required_fields(self, mock_form_valid, mock_get):
        if not settings.TF5_ENABLED:
            return
        self.login()
        url = reverse("tf5_create")
        mock_get.side_effect = self.mock_requests_get
        mock_form_valid.return_value = redirect(url)
        for required_field in (
            "cpr",
            "navn",
            "adresse",
            "postnummer",
            "by",
            "telefon",
            "bookingnummer",
            "leverandørfaktura_nummer",
            "leverandørfaktura",
            "indleveringsdato",
        ):
            data = {**self.formdata1}
            files = {**self.formfiles1}
            if required_field in data:
                del data[required_field]
            if required_field in files:
                del files[required_field]
            form = TF5Form(data=data, files=files)
            self.assertTrue(required_field in form.errors)
            self.assertEquals(form.errors[required_field], ["Dette felt er påkrævet."])
            html_errors = self.submit_get_errors(url, data)
            self.assertTrue(required_field in html_errors)
            self.assertEquals(html_errors[required_field], ["Dette felt er påkrævet."])

    def test_vareform_required_fields(self):
        if not settings.TF5_ENABLED:
            return
        varesatser = {
            1: Vareafgiftssats(
                id=1,
                afgiftstabel=1,
                vareart_da="Båthorn",
                vareart_kl="Båthorn",
                afgiftsgruppenummer=12345678,
                enhed=Vareafgiftssats.Enhed.KILOGRAM,
                afgiftssats="1.00",
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            ),
            2: Vareafgiftssats(
                id=2,
                afgiftstabel=1,
                vareart_da="Klovnesko",
                vareart_kl="Klovnesko",
                afgiftsgruppenummer=87654321,
                enhed=Vareafgiftssats.Enhed.ANTAL,
                afgiftssats="1.00",
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            ),
            3: Vareafgiftssats(
                id=3,
                afgiftstabel=1,
                vareart_da="Ethjulede cykler",
                vareart_kl="Ethjulede cykler",
                afgiftsgruppenummer=22446688,
                enhed=Vareafgiftssats.Enhed.PROCENT,
                afgiftssats="0.50",
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            ),
        }

        for required_field in ("vareafgiftssats",):
            data = {**self.subformdata1}
            del data[required_field]
            form = TF10VareForm(data=data, varesatser=varesatser)
            self.assertTrue(required_field in form.errors)
            self.assertEquals(form.errors[required_field], ["Dette felt er påkrævet."])

        for required_field, vareart in (
            ("mængde", 1),
            ("antal", 2),
            ("fakturabeløb", 3),
        ):
            data = {**self.subformdata1, "vareafgiftssats": vareart}
            del data[required_field]
            form = TF10VareForm(data=data, varesatser=varesatser)
            self.assertTrue(required_field in form.errors, required_field)
            self.assertEquals(
                form.errors[required_field], ["Dette felt er påkrævet."], required_field
            )

    @patch.object(requests.Session, "get")
    @patch.object(
        requests.Session,
        "post",
    )
    def test_form_successful(self, mock_post, mock_get):
        if not settings.TF5_ENABLED:
            return
        self.login()
        url = reverse("tf5_create")
        mock_get.side_effect = self.mock_requests_get
        mock_post.side_effect = self.mock_requests_post
        response = self.client.post(url, data={**self.formdata1, **self.formfiles1})
        self.assertEquals(response.status_code, 302, self.get_errors(response.content))
        prefix = f"{settings.REST_DOMAIN}/api/"
        posted_map = defaultdict(list)
        for url, data in self.posted:
            posted_map[url].append(json.loads(data))
        self.assertEquals(
            posted_map[prefix + "privat_afgiftsanmeldelse"],
            [
                {
                    "anonym": False,
                    "cpr": "1234567890",
                    "navn": "TestPerson1",
                    "adresse": "Testvej 42",
                    "postnummer": 1234,
                    "by": "TestBy",
                    "telefon": "123456",
                    "bookingnummer": "123",
                    "indleveringsdato": "2023-11-03",
                    "leverandørfaktura_nummer": "123",
                    "indførselstilladelse": None,
                    "leverandørfaktura_navn": "leverandørfaktura.txt",
                    "leverandørfaktura": base64.b64encode(
                        "Testtekst".encode("utf-8")
                    ).decode("ascii"),
                }
            ],
        )

    @patch.object(requests.Session, "get")
    @patch("ui.views.TF5FormCreateView.form_valid")
    def test_form_filefields_size(self, mock_form_valid, mock_get):
        if not settings.TF5_ENABLED:
            return
        self.login()
        url = reverse("tf5_create")
        mock_get.side_effect = self.mock_requests_get
        mock_form_valid.return_value = redirect(url)
        data = {**self.formdata1}
        files = {
            "leverandørfaktura": SimpleUploadedFile(
                "leverandørfaktura.txt", b"\x00" * 11000000
            ),
        }
        for v in files.values():
            v.seek(0)
        form = TF5Form(data=data, files=files)
        html_errors = self.submit_get_errors(url, {**data, **files})
        for file_field in ("leverandørfaktura",):
            self.assertTrue(file_field in form.errors)
            self.assertEquals(
                form.errors[file_field], ["Filen er for stor; den må max. være 10.0 MB"]
            )
            self.assertTrue(file_field in html_errors)
            self.assertEquals(
                html_errors[file_field], ["Filen er for stor; den må max. være 10.0 MB"]
            )
