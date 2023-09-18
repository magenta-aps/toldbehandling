import csv
import json
import re
import time
from collections import defaultdict
from copy import deepcopy
from datetime import timedelta, datetime
from io import BytesIO, StringIO
from typing import List, Tuple, Dict
from unittest.mock import patch, mock_open
from urllib.parse import quote, quote_plus, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup
from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook
from requests import Response
from told_common.rest_client import RestClient
from told_common.tests import (
    TemplateTagsTest,
    LoginTest,
    AnmeldelseListViewTest,
    modify_values,
)


class TestLogin(TestCase):
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

    @patch.object(requests, "post", return_value=create_response(401, "Unauthorized"))
    def test_incorrect_login(self, mock_method):
        response = self.client.post(reverse("login"), {"username": "incorrect"})
        self.assertEquals(response.status_code, 200)  # Rerender form
        mock_method.assert_not_called()
        errors = self.get_errors(response.content)
        self.assertEquals(errors["password"], ["Dette felt er påkrævet."])

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

    def test_token_refresh_expired(self):
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
        response = self.client.get(reverse("index"))
        self.assertEquals(response.status_code, 302)
        self.assertEquals(
            response.headers["Location"],
            "/login?next=" + quote_plus(reverse("index")),
        )


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


class TestGodkend(HasLogin, TestCase):
    def setUp(self):
        super().setUp()
        self.patched: List[Tuple[str, str]] = []

    def mock_requests_get(self, path):
        expected_prefix = "http://toldbehandling-rest:7000/api/"
        path = path.split("?")[0]
        path = path.rstrip("/")
        response = Response()
        json_content = None
        content = None
        status_code = None
        if path == expected_prefix + "vareafgiftssats/1":
            json_content = {
                "id": 1,
                "afgiftstabel": 1,
                "vareart": "Båthorn",
                "afgiftsgruppenummer": 1234567,
                "enhed": "kg",
                "afgiftssats": "1.00",
            }

        if path == expected_prefix + "afsender/1":
            json_content = {
                "id": 1,
                "navn": "Testfirma 1",
                "adresse": "Testvej 42",
                "postnummer": 1234,
                "by": "TestBy",
                "postbox": "123",
                "telefon": "123456",
                "cvr": 12345678,
            }

        if path == expected_prefix + "modtager/1":
            json_content = {
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

        if path == expected_prefix + "afgiftsanmeldelse/1":
            json_content = {
                "id": 1,
                "afsender": 1,
                "modtager": 1,
                "fragtforsendelse": 1,
                "postforsendelse": None,
                "leverandørfaktura_nummer": "1234",
                "leverandørfaktura": "/leverandørfakturaer/1/leverandørfaktura.txt",
                "modtager_betaler": False,
                "indførselstilladelse": "5678",
                "afgift_total": None,
                "betalt": False,
                "dato": "2023-08-22",
                "godkendt": False,
            }
        if path == expected_prefix + "fragtforsendelse/1":
            json_content = {
                "id": 1,
                "forsendelsestype": "S",
                "fragtbrevsnummer": 1,
                "fragtbrev": "/leverandørfakturaer/1/leverandørfaktura.txt",
            }

        if path == expected_prefix + "varelinje":
            json_content = {
                "count": 1,
                "items": [
                    {
                        "id": 1,
                        "afgiftsanmeldelse": 1,
                        "vareafgiftssats": 1,
                        "antal": 5,
                        "afgiftsbeløb": "5000.00",
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

    def mock_requests_patch(self, path, data, headers=None):
        expected_prefix = "http://toldbehandling-rest:7000/api/"
        path = path.rstrip("/")
        response = Response()
        json_content = None
        content = None
        status_code = None
        if path == expected_prefix + "afgiftsanmeldelse/1":
            json_content = {"id": 1}
            self.patched.append((path, data))
        if json_content:
            content = json.dumps(json_content).encode("utf-8")
        if content:
            if not status_code:
                status_code = 200
            response._content = content
        response.status_code = status_code or 404
        return response

    def mock_requests_error(self, path, *args, **kwargs):
        response = Response()
        response.status_code = 500
        return response

    def mock_requests_error_401(self, path, *args, **kwargs):
        response = Response()
        response.status_code = 401
        return response

    def test_requires_login(self):
        url = str(reverse("index"))
        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)
        self.assertEquals(
            response.headers["Location"],
            reverse("login") + "?next=" + quote(url, safe=""),
        )

    @patch.object(requests.Session, "get")
    def test_get_view(self, mock_get):
        self.login()
        url = reverse("tf10_view", kwargs={"id": 1})
        mock_get.side_effect = self.mock_requests_get
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    @patch.object(requests.Session, "get")
    def test_get_view_not_found(self, mock_get):
        self.login()
        url = reverse("tf10_view", kwargs={"id": 2})
        mock_get.side_effect = self.mock_requests_get
        response = self.client.get(url)
        self.assertEquals(response.status_code, 404)

    @patch.object(requests.Session, "patch")
    def test_post_view_godkend(self, mock_patch):
        self.login()
        view_url = reverse("tf10_view", kwargs={"id": 1})
        mock_patch.side_effect = self.mock_requests_patch
        response = self.client.post(view_url, {"godkendt": "true"})
        self.assertEquals(response.status_code, 302)
        prefix = "http://toldbehandling-rest:7000/api/"
        patched_map = defaultdict(list)
        for url, data in self.patched:
            patched_map[url].append(json.loads(data))
        self.assertEquals(
            patched_map[prefix + "afgiftsanmeldelse/1"], [{"godkendt": True}]
        )

    @patch.object(requests.Session, "patch")
    def test_post_view_afvis(self, mock_patch):
        self.login()
        view_url = reverse("tf10_view", kwargs={"id": 1})
        mock_patch.side_effect = self.mock_requests_patch
        response = self.client.post(view_url, {"godkendt": "false"})
        self.assertEquals(response.status_code, 302)
        prefix = "http://toldbehandling-rest:7000/api/"
        patched_map = defaultdict(list)
        for url, data in self.patched:
            patched_map[url].append(json.loads(data))
        self.assertEquals(
            patched_map[prefix + "afgiftsanmeldelse/1"], [{"godkendt": False}]
        )

    @patch.object(requests.Session, "patch")
    def test_post_view_not_found(self, mock_patch):
        self.login()
        view_url = reverse("tf10_view", kwargs={"id": 2})
        mock_patch.side_effect = self.mock_requests_patch
        response = self.client.post(view_url, {"godkendt": "true"})
        self.assertEquals(response.status_code, 404)
        prefix = "http://toldbehandling-rest:7000/api/"
        patched_map = defaultdict(list)
        for url, data in self.patched:
            patched_map[url].append(json.loads(data))
        self.assertEquals(patched_map[prefix + "afgiftsanmeldelse/2"], [])

    @patch.object(requests.Session, "get")
    def test_get_view_rest_error(self, mock_get):
        self.login()
        url = reverse("tf10_view", kwargs={"id": 1})
        mock_get.side_effect = self.mock_requests_error
        response = self.client.get(url)
        self.assertEquals(response.status_code, 500)

    @patch.object(requests.Session, "get")
    def test_get_view_rest_error_401(self, mock_get):
        self.login()
        url = reverse("tf10_view", kwargs={"id": 1})
        mock_get.side_effect = self.mock_requests_error_401
        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)

    @patch.object(requests.Session, "patch")
    def test_post_view_rest_error(self, mock_patch):
        self.login()
        view_url = reverse("tf10_view", kwargs={"id": 1})
        mock_patch.side_effect = self.mock_requests_error
        response = self.client.post(view_url, {"godkendt": "true"})
        self.assertEquals(response.status_code, 500)


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


class AdminTemplateTagsTest(TemplateTagsTest, TestCase):
    pass


class AdminLoginTest(LoginTest, TestCase):
    @property
    def restricted_url(self):
        return str(reverse("tf10_list"))


class AdminAnmeldelseListViewTest(AnmeldelseListViewTest, TestCase):
    can_view = True
    can_edit = False

    @property
    def list_url(self):
        return str(reverse("tf10_list"))

    def edit_url(self, id):
        return str(reverse("tf10_edit", kwargs={"id": id}))

    def view_url(self, id):
        return str(reverse("tf10_view", kwargs={"id": id}))


class AdminFileViewTest(FileViewTest, TestCase):
    @property
    def file_view_url(self):
        return str(reverse("fragtbrev_view", kwargs={"id": 1}))


class AfgiftstabelListViewTest(HasLogin, TestCase):
    @property
    def list_url(self):
        return reverse("afgiftstabel_list")

    def view_url(self, id):
        return reverse("afgiftstabel_view", kwargs={"id": id})

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
                "gyldig_fra": "2022-01-01",
                "gyldig_til": "2023-01-01",
                "kladde": False,
            },
            {
                "id": 2,
                "gyldig_fra": "2023-01-01",
                "gyldig_til": None,
                "kladde": False,
            },
            {
                "id": 3,
                "gyldig_fra": None,
                "gyldig_til": None,
                "kladde": True,
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
        if path == expected_prefix + "afgiftstabel":
            items = deepcopy(self.testdata)
            if "offset" in query:
                items = items[int(query["offset"][0]) :]
            if "limit" in query:
                items = items[: int(query["limit"][0])]
            sort = query.get("sort")
            reverse = query.get("order") == ["desc"]
            if sort == ["gyldig_fra"]:
                items.sort(
                    key=lambda x: (x["gyldig_fra"] is None, x["gyldig_fra"], x["id"]),
                    reverse=reverse,
                )
            elif sort == ["gyldig_til"]:
                items.sort(
                    key=lambda x: (x["gyldig_til"] is None, x["gyldig_til"], x["id"]),
                    reverse=reverse,
                )
            elif sort == ["kladde"]:
                items.sort(key=lambda x: (x["kladde"], x["id"]), reverse=reverse)

            json_content = {"count": len(items), "items": items}
        if json_content:
            content = json.dumps(json_content).encode("utf-8")
        if content:
            if not status_code:
                status_code = 200
            response._content = content
        response.status_code = status_code or 404
        return response

    def test_requires_login(self):
        url = self.list_url
        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)
        self.assertEquals(
            response.headers["Location"],
            reverse("login") + "?next=" + quote(url, safe=""),
        )

    @patch.object(requests.Session, "get")
    def test_list(self, mock_get):
        self.maxDiff = None
        mock_get.side_effect = self.mock_requests_get
        self.login()
        url = self.list_url
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        table_data = self.get_html_list(response.content)
        self.assertEquals(
            # Tag table_data og fjern alle html-tags i strengen. Join med mellemrum.
            self.strip_html_tags(table_data),
            [
                {
                    "Gyldig fra": "2022-01-01",
                    "Gyldig til": "2023-01-01",
                    "Kladde": "Nej",
                    "Handlinger": "Vis Download .xlsx .csv",
                },
                {
                    "Gyldig fra": "2023-01-01",
                    "Gyldig til": "",
                    "Kladde": "Nej",
                    "Handlinger": "Vis Download .xlsx .csv",
                },
                {
                    "Gyldig fra": "",
                    "Gyldig til": "",
                    "Kladde": "Ja",
                    "Handlinger": "Vis Download .xlsx .csv Slet",
                },
            ],
        )

        url = self.list_url + "?json=1"
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        data = response.json()

        self.assertEquals(
            self.strip_html_tags(data),
            {
                "total": 3,
                "items": [
                    {
                        "id": 1,
                        "gyldig_fra": "2022-01-01",
                        "gyldig_til": "2023-01-01",
                        "kladde": "nej",
                        "actions": "Vis Download .xlsx .csv",
                    },
                    {
                        "id": 2,
                        "gyldig_fra": "2023-01-01",
                        "gyldig_til": "",
                        "kladde": "nej",
                        "actions": "Vis Download .xlsx .csv",
                    },
                    {
                        "id": 3,
                        "gyldig_fra": "",
                        "gyldig_til": "",
                        "kladde": "ja",
                        "actions": "Vis Download .xlsx .csv Slet",
                    },
                ],
            },
        )

    @staticmethod
    def strip_html_tags(data: Dict) -> Dict:
        # Tag table_data og fjern alle html-tags i alle streng-values. Join med mellemrum.
        return modify_values(
            data,
            (str,),
            lambda s: " ".join(
                filter(
                    None,
                    [x.strip() for x in re.sub("<[^>]+>", "", s).split("\n")],
                )
            ),
        )

    @patch.object(requests.Session, "get")
    def test_list_sort(self, mock_get):
        mock_get.side_effect = self.mock_requests_get
        self.login()
        sort_tests = [
            ("gyldig_fra", "", [1, 2, 3]),
            ("gyldig_fra", "asc", [1, 2, 3]),
            ("gyldig_fra", "desc", [3, 2, 1]),
            ("gyldig_til", "", [1, 2, 3]),
            ("gyldig_til", "asc", [1, 2, 3]),
            ("gyldig_til", "desc", [3, 2, 1]),
            ("kladde", "", [1, 2, 3]),
            ("kladde", "asc", [1, 2, 3]),
            ("kladde", "desc", [3, 2, 1]),
        ]
        for test in sort_tests:
            url = self.list_url + f"?json=1&sort={test[0]}&order={test[1]}"
            response = self.client.get(url)
            numbers = [int(item["id"]) for item in response.json()["items"]]
            self.assertEquals(response.status_code, 200)
            self.assertEquals(numbers, test[2], f"{test[0]} {test[1]}")

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
            url = self.list_url + f"?json=1&offset={offset}&limit={limit}"
            response = self.client.get(url)
            numbers = [int(item["id"]) for item in response.json()["items"]]
            self.assertEquals(response.status_code, 200)
            self.assertEquals(numbers, expected)


class AfgiftstabelDownloadTest(HasLogin, TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.afgiftstabel = {
            "id": 1,
            "gyldig_fra": "2022-01-01",
            "gyldig_til": "2023-01-01",
            "kladde": False,
        }
        cls.afgiftssatser = [
            {
                "id": 1,
                "afgiftstabel": 1,
                "afgiftsgruppenummer": 70,
                "vareart": "FYRVÆRKERI",
                "enhed": "pct",
                "minimumsbeløb": False,
                "afgiftssats": "100.00",
                "kræver_indførselstilladelse": False,
            },
            {
                "id": 2,
                "afgiftstabel": 1,
                "afgiftsgruppenummer": 71,
                "vareart": "KNALLERTER",
                "enhed": "ant",
                "minimumsbeløb": False,
                "afgiftssats": "2530.00",
                "kræver_indførselstilladelse": False,
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
        if path == expected_prefix + "afgiftstabel/1":
            json_content = self.afgiftstabel
        if path == expected_prefix + "vareafgiftssats":
            json_content = {
                "count": len(self.afgiftssatser),
                "items": self.afgiftssatser,
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
    def test_xlsx(self, mock_get):
        mock_get.side_effect = self.mock_requests_get
        self.login()
        response = self.client.get(
            reverse("afgiftstabel_download", kwargs={"id": 1, "format": "xlsx"})
        )
        self.assertEquals(response.status_code, 200)
        self.assertEquals(
            response.headers["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertTrue(len(response.content) > 0)
        workbook = load_workbook(BytesIO(response.content))
        self.assertEquals(
            list(workbook.active.values),
            [
                (
                    "Afgiftsgruppenummer",
                    "Overordnet",
                    "Vareart",
                    "Enhed",
                    "Afgiftssats",
                    "Kræver indførselstilladelse",
                    "Minimumsbeløb",
                    "Segment nedre",
                    "Segment øvre",
                ),
                (
                    70,
                    None,
                    "FYRVÆRKERI",
                    "procent",
                    "100,00",
                    "nej",
                    "0,00",
                    None,
                    None,
                ),
                (
                    71,
                    None,
                    "KNALLERTER",
                    "antal",
                    "2.530,00",
                    "nej",
                    "0,00",
                    None,
                    None,
                ),
            ],
        )

    @patch.object(requests.Session, "get")
    def test_csv(self, mock_get):
        mock_get.side_effect = self.mock_requests_get
        self.login()
        response = self.client.get(
            reverse("afgiftstabel_download", kwargs={"id": 1, "format": "csv"})
        )
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.headers["Content-Type"], "text/csv")
        self.assertTrue(len(response.content) > 0)
        reader = csv.reader(StringIO(response.content.decode("utf-8")))
        self.assertEquals(
            [row for row in reader],
            [
                [
                    "Afgiftsgruppenummer",
                    "Overordnet",
                    "Vareart",
                    "Enhed",
                    "Afgiftssats",
                    "Kræver indførselstilladelse",
                    "Minimumsbeløb",
                    "Segment nedre",
                    "Segment øvre",
                ],
                ["70", "", "FYRVÆRKERI", "procent", "100,00", "nej", "0,00", "", ""],
                ["71", "", "KNALLERTER", "antal", "2.530,00", "nej", "0,00", "", ""],
            ],
        )
