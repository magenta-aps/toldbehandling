import base64
import json
import time
from collections import defaultdict
from copy import deepcopy
from datetime import timedelta, datetime
from typing import List, Tuple
from unittest.mock import patch, mock_open
from urllib.parse import quote, quote_plus, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup
from django.core.files.uploadedfile import SimpleUploadedFile, TemporaryUploadedFile
from django.shortcuts import redirect
from django.test import TestCase
from django.urls import reverse
from requests import Response
from told_common.rest_client import RestClient
from told_common.tests import TemplateTagsTest
from ui.forms import TF10Form, TF10VareForm


class LoginTest(TestCase):
    @staticmethod
    def create_response(status_code, content):
        response = Response()
        response.status_code = status_code
        if type(content) in (dict, list):
            content = json.dumps(content)
        if type(content) is str:
            content = content.encode("utf-8")
        response._content = content
        return response

    @patch.object(requests, "post", return_value=create_response(401, "Unauthorized"))
    def test_incorrect_login(self, mock_method):
        response = self.client.post(
            reverse("login"), {"username": "incorrect", "password": "credentials"}
        )
        self.assertEquals(response.status_code, 200)  # Rerender form
        mock_method.assert_called_with(
            "http://toldbehandling-rest:7000/api/token/pair",
            json={"username": "incorrect", "password": "credentials"},
            headers={"Content-Type": "application/json"},
        )

    @patch.object(
        requests,
        "post",
        return_value=create_response(200, {"access": "123456", "refresh": "abcdef"}),
    )
    def test_correct_login(self, mock_method):
        response = self.client.post(
            reverse("login") + "?next=/",
            {"username": "correct", "password": "credentials"},
        )
        mock_method.assert_called_with(
            "http://toldbehandling-rest:7000/api/token/pair",
            json={"username": "correct", "password": "credentials"},
            headers={"Content-Type": "application/json"},
        )
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response.headers["Location"], "/")
        self.assertEquals(response.cookies["access_token"].value, "123456")
        self.assertEquals(response.cookies["refresh_token"].value, "abcdef")

    @patch.object(RestClient, "refresh_login")
    @patch.object(
        requests.Session,
        "get",
        return_value=create_response(200, {"count": 0, "items": []}),
    )
    @patch.object(
        requests,
        "post",
        return_value=create_response(200, {"access": "123456", "refresh": "abcdef"}),
    )
    def test_token_refresh_not_needed(self, mock_post, mock_get, mock_refresh_login):
        self.client.post(
            reverse("login"), {"username": "correct", "password": "credentials"}
        )
        self.client.get(reverse("rest", kwargs={"path": "afsender"}))
        # Check that token refresh is not needed
        mock_refresh_login.assert_not_called()
        with self.settings(NINJA_JWT={"ACCESS_TOKEN_LIFETIME": timedelta(seconds=1)}):
            self.client.get(reverse("rest", kwargs={"path": "afsender"}))
            # Check that token refresh is needed
            mock_refresh_login.assert_called()

    @patch.object(RestClient, "refresh_login")
    @patch.object(
        requests.Session,
        "get",
        return_value=create_response(200, {"count": 0, "items": []}),
    )
    @patch.object(
        requests,
        "post",
        return_value=create_response(200, {"access": "123456", "refresh": "abcdef"}),
    )
    def test_token_refresh_needed(self, mock_post, mock_get, mock_refresh_login):
        self.client.post(
            reverse("login"), {"username": "correct", "password": "credentials"}
        )
        self.client.get(reverse("rest", kwargs={"path": "afsender"}))
        # Check that token refresh is not needed
        mock_refresh_login.assert_not_called()
        # Set token max_age way down, so it will be refreshed
        with self.settings(NINJA_JWT={"ACCESS_TOKEN_LIFETIME": timedelta(seconds=1)}):
            self.client.get(reverse("rest", kwargs={"path": "afsender"}))
            # Check that token refresh is needed
            mock_refresh_login.assert_called()

    @patch.object(
        requests.Session,
        "get",
        return_value=create_response(200, {"count": 0, "items": []}),
    )
    @patch.object(
        requests,
        "post",
        return_value=create_response(200, {"access": "123456", "refresh": "abcdef"}),
    )
    def test_token_refresh(self, mock_post, mock_get):
        self.client.post(
            reverse("login"), {"username": "correct", "password": "credentials"}
        )
        mock_post.return_value = self.create_response(200, {"access": "7890ab"})
        # Set token max_age way down, so it will be refreshed
        with self.settings(NINJA_JWT={"ACCESS_TOKEN_LIFETIME": timedelta(seconds=1)}):
            response = self.client.get(reverse("rest", kwargs={"path": "afsender"}))
            # Check that token refresh is needed
            self.assertEquals(response.cookies["access_token"].value, "7890ab")

    @patch.object(
        requests,
        "post",
        return_value=create_response(200, {"access": "123456", "refresh": "abcdef"}),
    )
    def test_logout(self, mock_post):
        response = self.client.post(
            reverse("login") + "?next=/",
            {"username": "correct", "password": "credentials"},
        )
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response.headers["Location"], "/")
        self.assertEquals(response.cookies["access_token"].value, "123456")
        self.assertEquals(response.cookies["refresh_token"].value, "abcdef")
        response = self.client.get(reverse("logout"))
        self.assertEquals(response.cookies["access_token"].value, "")
        self.assertEquals(response.cookies["refresh_token"].value, "")

    @patch.object(
        requests.Session,
        "get",
        return_value=create_response(401, ""),
    )
    def test_token_refresh_expired(self, mock_get):
        self.client.cookies.load(
            {
                "access_token": "123456",
                "refresh_token": "abcdef",
                "access_token_timestamp": time.time(),
                "refresh_token_timestamp": (
                    datetime.now() - timedelta(days=2)
                ).timestamp(),
            }
        )
        response = self.client.get(reverse("tf10_create"))
        self.assertEquals(response.status_code, 302)
        self.assertEquals(
            response.headers["Location"],
            "/login?next=" + quote_plus(reverse("tf10_create")),
        )
        mock_get.return_value = self.create_response(500, "")
        response = self.client.get(reverse("tf10_create"))
        self.assertEquals(response.status_code, 302)


class HasLogin:
    def login(self):
        self.client.cookies.load(
            {
                "access_token": "123456",
                "refresh_token": "abcdef",
                "access_token_timestamp": time.time(),
                "refresh_token_timestamp": time.time(),
            }
        )


class BlanketTest(HasLogin, TestCase):
    formdata1 = {
        "afsender_cvr": "12345678",
        "afsender_navn": "TestFirma1",
        "afsender_adresse": "Testvej 42",
        "afsender_postnummer": "1234",
        "afsender_by": "TestBy",
        "afsender_postbox": "123",
        "afsender_telefon": "123456",
        "modtager_cvr": "12345679",
        "modtager_navn": "TestFirma2",
        "modtager_adresse": "Testvej 43",
        "modtager_postnummer": "1234",
        "modtager_by": "TestBy",
        "modtager_postbox": "124",
        "modtager_telefon": "123123",
        "modtager_indførselstilladelse": "123",
        "leverandørfaktura_nummer": "123",
        "fragttype": "skibsfragt",
        "fragtbrevnr": "123",
        "form-TOTAL_FORMS": "1",
        "form-INITIAL_FORMS": "1",
        "form-0-vareart": "1",
        "form-0-mængde": "3",
        "form-0-antal": "6",
        "form-0-fakturabeløb": "100.00",
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
        "vareart": "1",
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

    def test_requires_login(self):
        url = str(reverse("tf10_create"))
        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)
        self.assertEquals(
            response.headers["Location"],
            reverse("login") + "?next=" + quote(url, safe=""),
        )

    def mock_requests_get(self, path):
        expected_prefix = "http://toldbehandling-rest:7000/api/"
        path = path.split("?")[0]
        path = path.rstrip("/")
        response = Response()
        json_content = None
        content = None
        status_code = None
        empty = {"count": 0, "items": []}
        if path == expected_prefix + "vareafgiftssats":
            if self.mock_existing["vareafgiftssats"]:
                json_content = {
                    "count": 1,
                    "items": [
                        {
                            "id": 1,
                            "afgiftstabel": 1,
                            "vareart": "Båthorn",
                            "afgiftsgruppenummer": 1234567,
                            "enhed": "kg",
                            "afgiftssats": "1.00",
                        }
                    ],
                }
            else:
                json_content = empty
        if path == expected_prefix + "afsender":
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
        if path == expected_prefix + "modtager":
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
                            "indførselstilladelse": 123,
                        }
                    ],
                }
            else:
                json_content = empty
        if json_content:
            content = json.dumps(json_content).encode("utf-8")
        if content:
            if not status_code:
                status_code = 200
            response._content = content
        response.status_code = status_code or 404
        return response

    def mock_requests_post(self, path, data, headers=None):
        expected_prefix = "http://toldbehandling-rest:7000/api/"
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

    @staticmethod
    def get_errors(html: str):
        soup = BeautifulSoup(html, "html.parser")
        error_fields = {}
        for element in soup.find_all(class_="is-invalid"):
            el = element
            for i in range(1, 3):
                el = el.parent
                errorlist = el.find(class_="errorlist")
                if errorlist:
                    error_fields[element["name"]] = [
                        li.text for li in errorlist.find_all(name="li")
                    ]
                    break
        all_errors = soup.find(
            lambda tag: tag.has_attr("class")
            and "errorlist" in tag["class"]
            and "nonfield" in tag["class"]
        )
        if all_errors:
            error_fields["__all__"] = [li.text for li in all_errors.find_all(name="li")]
        return error_fields

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
            "modtager_indførselstilladelse",
            "fragttype",
            "forbindelsesnr",
            "fragtbrevnr",
            "leverandørfaktura",
            "leverandørfaktura_nummer",
            "fragtbrev",
            "form-0-vareart",
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
    @patch("ui.views.TF10FormView.form_valid")
    def test_form_required_fields(self, mock_form_valid, mock_get):
        self.login()
        url = reverse("tf10_create")
        mock_get.side_effect = self.mock_requests_get
        mock_form_valid.return_value = redirect(reverse("tf10_create"))
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
        del files["fragtbrev"]
        form = TF10Form(data=self.formdata1, files=files)
        self.assertEquals(form.errors["fragtbrev"], ["Mangler fragtbrev"])
        html_errors = self.submit_get_errors(url, {**self.formdata1, **files})
        self.assertEquals(html_errors["fragtbrev"], ["Mangler fragtbrev"])

    def test_vareform_required_fields(self):
        varesatser = {
            1: {
                "id": 1,
                "afgiftstabel": 1,
                "vareart": "Båthorn",
                "afgiftsgruppenummer": 12345678,
                "enhed": "kg",
                "afgiftssats": "1.00",
            },
            2: {
                "id": 2,
                "afgiftstabel": 1,
                "vareart": "Klovnesko",
                "afgiftsgruppenummer": 87654321,
                "enhed": "ant",
                "afgiftssats": "1.00",
            },
        }

        for required_field in (
            "vareart",
            "fakturabeløb",
        ):
            data = {**self.subformdata1}
            del data[required_field]
            form = TF10VareForm(data=data, varesatser=varesatser)
            self.assertTrue(required_field in form.errors)
            self.assertEquals(form.errors[required_field], ["Dette felt er påkrævet."])

        for required_field, vareart in (("mængde", 1), ("antal", 2)):
            data = {**self.subformdata1, "vareart": vareart}
            del data[required_field]
            form = TF10VareForm(data=data, varesatser=varesatser)
            self.assertTrue(required_field in form.errors)
            self.assertEquals(form.errors[required_field], ["Dette felt er påkrævet."])

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
        prefix = "http://toldbehandling-rest:7000/api/"
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
                    "indførselstilladelse": "123",
                }
            ],
        )
        self.assertEquals(
            posted_map[prefix + "fragtforsendelse"],
            [
                {
                    "fragtbrevsnummer": "123",
                    "forsendelsestype": "S",
                    "fragtbrev": base64.b64encode("Testtekst".encode("utf-8")).decode(
                        "ascii"
                    ),
                    "fragtbrev_navn": "fragtbrev.txt",
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
        prefix = "http://toldbehandling-rest:7000/api/"
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
                    "forsendelsestype": "S",
                    "fragtbrev": base64.b64encode("Testtekst".encode("utf-8")).decode(
                        "ascii"
                    ),
                    "fragtbrev_navn": "fragtbrev.txt",
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
        prefix = "http://toldbehandling-rest:7000/api/"
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
                    "indførselstilladelse": "123",
                }
            ],
        )
        self.assertEquals(
            posted_map[prefix + "postforsendelse"],
            [
                {
                    "postforsendelsesnummer": "123",
                    "forsendelsestype": "F",
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
                }
            ],
        )

    @patch.object(requests.Session, "get")
    @patch("ui.views.TF10FormView.form_valid")
    def test_form_filefields_size(self, mock_form_valid, mock_get):
        self.login()
        url = reverse("tf10_create")
        mock_get.side_effect = self.mock_requests_get
        mock_form_valid.return_value = redirect(reverse("tf10_create"))
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


class FileViewTest(HasLogin, TestCase):
    def mock_requests_get(self, path):
        expected_prefix = "http://toldbehandling-rest:7000/api/"
        path = path.split("?")[0]
        path = path.rstrip("/")
        response = Response()
        json_content = None
        content = None
        status_code = None
        if path == expected_prefix + "fragtforsendelse/1":
            json_content = {
                "id": 1,
                "forsendelsestype": "S",
                "fragtbrevsnummer": 1,
                "fragtbrev": "/leverandørfakturaer/1/leverandørfaktura.txt",
            }
        if json_content:
            content = json.dumps(json_content).encode("utf-8")
        if content:
            if not status_code:
                status_code = 200
            response._content = content
        response.status_code = status_code or 404
        return response

    @patch.object(requests.Session, "get")
    @patch("builtins.open", mock_open(read_data=b"test_data"))
    def test_fileview(self, mock_get):
        self.login()
        url = reverse("fragtbrev_view", kwargs={"id": 1})
        mock_get.side_effect = self.mock_requests_get
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        content = list(response.streaming_content)[0]
        self.assertEquals(content, b"test_data")


class UiTemplateTagsTest(TemplateTagsTest):
    pass


class ListViewTest(HasLogin, TestCase):
    @staticmethod
    def get_html_list(html: str):
        soup = BeautifulSoup(html, "html.parser")
        headers = [element.text for element in soup.css.select("table thead tr th")]
        return [
            dict(zip(headers, [td.text.strip() for td in row.select("td")]))
            for row in soup.css.select("table tbody tr")
        ]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.testdata = [
            {
                "id": 1,
                "leverandørfaktura_nummer": "12345",
                "modtager_betaler": False,
                "indførselstilladelse": "abcde",
                "betalt": False,
                "leverandørfaktura": "/leverand%C3%B8rfakturaer/10/leverand%C3%B8rfaktura.pdf",
                "afsender": {
                    "id": 20,
                    "navn": "Testfirma 5",
                    "adresse": "Testvej 42",
                    "postnummer": 1234,
                    "by": "TestBy",
                    "postbox": "123",
                    "telefon": "123456",
                    "cvr": 12345678,
                },
                "modtager": {
                    "id": 21,
                    "navn": "Testfirma 3",
                    "adresse": "Testvej 42",
                    "postnummer": 1234,
                    "by": "TestBy",
                    "postbox": "123",
                    "telefon": "123456",
                    "cvr": 12345678,
                    "kreditordning": True,
                    "indførselstilladelse": 123,
                },
                "postforsendelse": {
                    "id": 1,
                    "postforsendelsesnummer": "1234",
                    "forsendelsestype": "S",
                },
                "dato": "2023-09-03",
                "afgift_total": None,
                "fragtforsendelse": None,
                "godkendt": True,
            },
            {
                "id": 2,
                "leverandørfaktura_nummer": "12345",
                "modtager_betaler": False,
                "indførselstilladelse": "abcde",
                "betalt": False,
                "leverandørfaktura": "/leverand%C3%B8rfakturaer/10/leverand%C3%B8rfaktura.pdf",
                "afsender": {
                    "id": 22,
                    "navn": "Testfirma 4",
                    "adresse": "Testvej 42",
                    "postnummer": 1234,
                    "by": "TestBy",
                    "postbox": "123",
                    "telefon": "123456",
                    "cvr": 12345678,
                },
                "modtager": {
                    "id": 23,
                    "navn": "Testfirma 1",
                    "adresse": "Testvej 42",
                    "postnummer": 1234,
                    "by": "TestBy",
                    "postbox": "123",
                    "telefon": "123456",
                    "cvr": 12345678,
                    "kreditordning": True,
                    "indførselstilladelse": 123,
                },
                "postforsendelse": {
                    "id": 2,
                    "postforsendelsesnummer": "1234",
                    "forsendelsestype": "S",
                },
                "dato": "2023-09-02",
                "afgift_total": None,
                "fragtforsendelse": None,
                "godkendt": False,
            },
            {
                "id": 3,
                "leverandørfaktura_nummer": "12345",
                "modtager_betaler": False,
                "indførselstilladelse": "abcde",
                "betalt": False,
                "leverandørfaktura": "/leverand%C3%B8rfakturaer/10/leverand%C3%B8rfaktura.pdf",
                "afsender": {
                    "id": 24,
                    "navn": "Testfirma 6",
                    "adresse": "Testvej 42",
                    "postnummer": 1234,
                    "by": "TestBy",
                    "postbox": "123",
                    "telefon": "123456",
                    "cvr": 12345678,
                },
                "modtager": {
                    "id": 25,
                    "navn": "Testfirma 2",
                    "adresse": "Testvej 42",
                    "postnummer": 1234,
                    "by": "TestBy",
                    "postbox": "123",
                    "telefon": "123456",
                    "cvr": 12345678,
                    "kreditordning": True,
                    "indførselstilladelse": 123,
                },
                "postforsendelse": {
                    "id": 3,
                    "postforsendelsesnummer": "1234",
                    "forsendelsestype": "S",
                },
                "dato": "2023-09-01",
                "afgift_total": None,
                "fragtforsendelse": None,
                "godkendt": None,
            },
        ]

    def mock_requests_get(self, path):
        expected_prefix = "/api/"
        p = urlparse(path)
        path = p.path
        query = parse_qs(p.query)
        path = path.rstrip("/")
        response = Response()
        json_content = None
        content = None
        status_code = None
        if path == expected_prefix + "afgiftsanmeldelse/full":
            items = deepcopy(self.testdata)
            if "dato_før" in query:
                items = list(filter(lambda i: i["dato"] < query["dato_før"][0], items))
            if "dato_efter" in query:
                items = list(
                    filter(lambda i: i["dato"] >= query["dato_efter"][0], items)
                )
            if "offset" in query:
                items = items[int(query["offset"][0]) :]
            if "limit" in query:
                items = items[: int(query["limit"][0])]
            sort = query.get("sort")
            reverse = query.get("order") == ["desc"]
            if sort == ["afsender"]:
                items.sort(key=lambda x: x["afsender"]["navn"], reverse=reverse)
            elif sort == ["modtager"]:
                items.sort(key=lambda x: x["modtager"]["navn"], reverse=reverse)
            elif sort == ["dato"]:
                items.sort(key=lambda x: x["dato"], reverse=reverse)
            elif sort == ["godkendt"]:
                items.sort(
                    key=lambda x: (x["godkendt"] is None, x["godkendt"]),
                    reverse=reverse,
                )

            json_content = {"count": len(items), "items": items}
        if path == expected_prefix + "vareafgiftssats":
            json_content = {
                "count": 1,
                "items": [
                    {
                        "id": 1,
                        "afgiftstabel": 1,
                        "vareart": "Båthorn",
                        "afgiftsgruppenummer": 1234567,
                        "enhed": "kg",
                        "afgiftssats": "1.00",
                    }
                ],
            }
        if json_content:
            content = json.dumps(json_content).encode("utf-8")
        if content:
            if not status_code:
                status_code = 200
            response._content = content
        response.status_code = status_code or 404
        return response

    def test_requires_login(self):
        url = str(reverse("tf10_list"))
        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)
        self.assertEquals(
            response.headers["Location"],
            reverse("login") + "?next=" + quote(url, safe=""),
        )

    @patch.object(requests.Session, "get")
    def test_list(self, mock_get):
        mock_get.side_effect = self.mock_requests_get
        self.login()
        url = str(reverse("tf10_list"))
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        table_data = self.get_html_list(response.content)
        self.assertEquals(
            table_data,
            [
                {
                    "Nummer": "1",
                    "Dato": "2023-09-03",
                    "Afsender": "Testfirma 5",
                    "Modtager": "Testfirma 3",
                    "Status": "Godkendt",
                    "Handlinger": "",
                },
                {
                    "Nummer": "2",
                    "Dato": "2023-09-02",
                    "Afsender": "Testfirma 4",
                    "Modtager": "Testfirma 1",
                    "Status": "Afvist",
                    "Handlinger": "",
                },
                {
                    "Nummer": "3",
                    "Dato": "2023-09-01",
                    "Afsender": "Testfirma 6",
                    "Modtager": "Testfirma 2",
                    "Status": "Ny",
                    "Handlinger": "Redigér",
                },
            ],
        )

        url = str(reverse("tf10_list")) + "?json=1"
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        data = response.json()
        self.assertEquals(
            data,
            {
                "total": 3,
                "items": [
                    {
                        "id": 1,
                        "dato": "2023-09-03",
                        "afsender": "Testfirma 5",
                        "modtager": "Testfirma 3",
                        "godkendt": "Godkendt",
                        "actions": "",
                    },
                    {
                        "id": 2,
                        "dato": "2023-09-02",
                        "afsender": "Testfirma 4",
                        "modtager": "Testfirma 1",
                        "godkendt": "Afvist",
                        "actions": "",
                    },
                    {
                        "id": 3,
                        "dato": "2023-09-01",
                        "afsender": "Testfirma 6",
                        "modtager": "Testfirma 2",
                        "godkendt": "Ny",
                        "actions": '<a class="btn btn-primary btn-sm" href="something3">Redigér</a>',
                    },
                ],
            },
        )

    @patch.object(requests.Session, "get")
    def test_list_sort(self, mock_get):
        mock_get.side_effect = self.mock_requests_get
        self.login()
        sort_tests = [
            ("afsender", "", [2, 1, 3]),
            ("afsender", "asc", [2, 1, 3]),
            ("afsender", "desc", [3, 1, 2]),
            ("modtager", "", [2, 3, 1]),
            ("modtager", "asc", [2, 3, 1]),
            ("modtager", "desc", [1, 3, 2]),
            ("dato", "", [3, 2, 1]),
            ("dato", "asc", [3, 2, 1]),
            ("dato", "desc", [1, 2, 3]),
            ("godkendt", "", [2, 1, 3]),
            ("godkendt", "asc", [2, 1, 3]),
            ("godkendt", "desc", [3, 1, 2]),
        ]
        for test in sort_tests:
            url = str(reverse("tf10_list")) + f"?json=1&sort={test[0]}&order={test[1]}"
            response = self.client.get(url)
            numbers = [int(item["id"]) for item in response.json()["items"]]
            self.assertEquals(response.status_code, 200)
            self.assertEquals(numbers, test[2])

    @patch.object(requests.Session, "get")
    def test_list_filter(self, mock_get):
        mock_get.side_effect = self.mock_requests_get
        self.login()
        filter_tests = [
            ("dato_før", "2023-09-01", set()),
            ("dato_før", "2023-09-02", {3}),
            ("dato_før", "2023-09-03", {3, 2}),
            ("dato_før", "2023-09-04", {3, 2, 1}),
            ("dato_efter", "2023-09-01", {1, 2, 3}),
            ("dato_efter", "2023-09-02", {1, 2}),
            ("dato_efter", "2023-09-03", {1}),
            ("dato_efter", "2023-09-04", set()),
        ]
        for field, value, expected in filter_tests:
            url = str(reverse("tf10_list")) + f"?json=1&{field}={value}"
            response = self.client.get(url)
            self.assertEquals(response.status_code, 200)
            numbers = [int(item["id"]) for item in response.json()["items"]]
            self.assertEquals(set(numbers), expected)

    @patch.object(requests.Session, "get")
    def test_list_paginate(self, mock_get):
        mock_get.side_effect = self.mock_requests_get
        self.login()
        paginate_tests = [
            (-1, 3, [1, 2, 3]),
            (0, 3, [1, 2, 3]),
            (1, 3, [2, 3]),
            (2, 3, [3]),
            (0, 2, [1, 2]),
            (1, 2, [2, 3]),
            (2, 2, [3]),
            (0, 1, [1]),
            (1, 1, [2]),
            (2, 1, [3]),
            (0, 0, [1]),
            (1, 0, [2]),
            (2, 0, [3]),
        ]
        for offset, limit, expected in paginate_tests:
            url = str(reverse("tf10_list")) + f"?json=1&offset={offset}&limit={limit}"
            response = self.client.get(url)
            numbers = [int(item["id"]) for item in response.json()["items"]]
            self.assertEquals(response.status_code, 200)
            self.assertEquals(numbers, expected)

    @patch.object(requests.Session, "get")
    def test_form_invalid(self, mock_get):
        mock_get.side_effect = self.mock_requests_get
        invalid = {
            "dato_efter": ["fejl", "0", "-1", "2023-13-01", "2023-02-29"],
            "dato_før": ["fejl", "0", "-1", "2023-13-01", "2023-02-29"],
            "vareart": [-1, 10000000, "a"],
        }
        self.login()
        for field, values in invalid.items():
            for value in values:
                url = str(reverse("tf10_list")) + f"?json=1&{field}={value}"
                response = self.client.get(url)
                self.assertEquals(response.status_code, 400)
                data = response.json()
                self.assertTrue("error" in data)
                self.assertTrue(field in data["error"])

                url = str(reverse("tf10_list")) + f"?{field}={value}"
                response = self.client.get(url)
                self.assertEquals(response.status_code, 200)
                soup = BeautifulSoup(response.content, "html.parser")
                error_fields = [
                    element["name"] for element in soup.find_all(class_="is-invalid")
                ]
                self.assertEquals(error_fields, [field])
