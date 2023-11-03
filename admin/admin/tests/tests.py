# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import csv
import json
import re
import time
import traceback
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO, StringIO
from typing import Dict, List, Tuple
from unittest.mock import mock_open, patch
from urllib.parse import parse_qs, quote, quote_plus, urlparse

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.views.generic import TemplateView
from openpyxl import Workbook, load_workbook
from requests import Response
from told_common.data import Notat, Vareafgiftssats
from told_common.rest_client import RestClient
from told_common.views import FragtbrevView

from admin.views import TF10EditMultipleView

from admin.views import (  # isort: skip
    TF10FormUpdateView,
    TF10HistoryDetailView,
    TF10HistoryListView,
)

from admin.views import (  # isort: skip
    AfgiftstabelDownloadView,
    AfgiftstabelListView,
    TF10ListView,
    TF10View,
)
from told_common.tests import (  # isort: skip
    AnmeldelseListViewTest,
    HasLogin,
    LoginTest,
    PermissionsTest,
    TemplateTagsTest,
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

    @staticmethod
    def mock_requests_get(path):
        expected_prefix = f"{settings.REST_DOMAIN}/api/"
        path = path.split("?")[0]
        path = path.rstrip("/")
        response = Response()
        status_code = None
        if path == expected_prefix + "user":
            json_content = {
                "username": "admin",
                "first_name": "Administrator",
                "last_name": "",
                "email": "admin@told.gl",
                "is_superuser": True,
            }
        else:
            json_content = {"count": 0, "items": []}
        content = json.dumps(json_content).encode("utf-8")
        if content:
            if not status_code:
                status_code = 200
            response._content = content
        response.status_code = status_code or 404
        return response

    @patch.object(requests.sessions.Session, "get")
    @patch.object(requests, "post", return_value=create_response(401, "Unauthorized"))
    def test_incorrect_login(self, mock_post, mock_get):
        mock_get.side_effect = self.mock_requests_get
        response = self.client.post(reverse("login"), {"username": "incorrect"})
        self.assertEquals(response.status_code, 200)  # Rerender form
        mock_post.assert_not_called()
        errors = self.get_errors(response.content)
        self.assertEquals(errors["password"], ["Dette felt er påkrævet."])

        response = self.client.post(
            reverse("login"), {"username": "incorrect", "password": "credentials"}
        )
        self.assertEquals(response.status_code, 200)  # Rerender form
        mock_post.assert_called_with(
            f"{settings.REST_DOMAIN}/api/token/pair",
            json={"username": "incorrect", "password": "credentials"},
            headers={"Content-Type": "application/json"},
        )

    @patch.object(requests.sessions.Session, "get")
    @patch.object(
        requests,
        "post",
        return_value=create_response(200, {"access": "123456", "refresh": "abcdef"}),
    )
    def test_correct_login(self, mock_post, mock_get):
        mock_get.side_effect = self.mock_requests_get
        response = self.client.post(
            reverse("login") + "?back=/",
            {"username": "correct", "password": "credentials"},
        )
        mock_post.assert_called_with(
            f"{settings.REST_DOMAIN}/api/token/pair",
            json={"username": "correct", "password": "credentials"},
            headers={"Content-Type": "application/json"},
        )
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response.headers["Location"], "/")
        self.assertEquals(self.client.session["access_token"], "123456")
        self.assertEquals(self.client.session["refresh_token"], "abcdef")

    @patch.object(RestClient, "refresh_login")
    @patch.object(
        requests.sessions.Session,
        "get",
    )
    @patch.object(
        requests,
        "post",
        return_value=create_response(200, {"access": "123456", "refresh": "abcdef"}),
    )
    def test_token_refresh_not_needed(self, mock_post, mock_get, mock_refresh_login):
        mock_get.side_effect = self.mock_requests_get
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
        requests.sessions.Session,
        "get",
    )
    @patch.object(
        requests,
        "post",
        return_value=create_response(200, {"access": "123456", "refresh": "abcdef"}),
    )
    def test_token_refresh_needed(self, mock_post, mock_get, mock_refresh_login):
        mock_get.side_effect = self.mock_requests_get
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
        requests.sessions.Session,
        "get",
    )
    @patch.object(
        requests,
        "post",
        return_value=create_response(200, {"access": "123456", "refresh": "abcdef"}),
    )
    def test_token_refresh(self, mock_post, mock_get):
        mock_get.side_effect = self.mock_requests_get
        self.client.post(
            reverse("login"), {"username": "correct", "password": "credentials"}
        )
        mock_post.return_value = self.create_response(200, {"access": "7890ab"})
        # Set token max_age way down, so it will be refreshed
        with self.settings(NINJA_JWT={"ACCESS_TOKEN_LIFETIME": timedelta(seconds=1)}):
            response = self.client.get(reverse("rest", kwargs={"path": "afsender"}))
            # Check that token refresh is needed
            self.assertEquals(self.client.session["access_token"], "7890ab")

    @patch.object(requests.sessions.Session, "get")
    @patch.object(
        requests,
        "post",
        return_value=create_response(200, {"access": "123456", "refresh": "abcdef"}),
    )
    def test_logout(self, mock_post, mock_get):
        mock_get.side_effect = self.mock_requests_get
        response = self.client.post(
            reverse("login") + "?back=/",
            {"username": "correct", "password": "credentials"},
        )
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response.headers["Location"], "/")
        self.assertEquals(self.client.session["access_token"], "123456")
        self.assertEquals(self.client.session["refresh_token"], "abcdef")
        response = self.client.get(reverse("logout"))
        self.assertNotIn("access_token", self.client.session)
        self.assertNotIn("refresh_token", self.client.session)

    def test_token_refresh_expired(self):
        session = self.client.session
        session.update(
            {
                "access_token": "123456",
                "refresh_token": "abcdef",
                "access_token_timestamp": time.time(),
                "refresh_token_timestamp": (
                    datetime.now() - timedelta(days=2)
                ).timestamp(),
            }
        )
        session.save()
        session_cookie = settings.SESSION_COOKIE_NAME
        self.client.cookies[session_cookie] = session.session_key
        cookie_data = {
            "max-age": None,
            "path": "/",
            "domain": settings.SESSION_COOKIE_DOMAIN,
            "secure": settings.SESSION_COOKIE_SECURE or None,
            "expires": None,
        }
        self.client.cookies[session_cookie].update(cookie_data)

        response = self.client.get(reverse("index"))
        self.assertEquals(response.status_code, 302)
        self.assertEquals(
            response.headers["Location"],
            "/login?back=" + quote_plus(reverse("index")),
        )


class TestGodkend(PermissionsTest, TestCase):
    view = TF10View

    check_permissions = (
        (reverse("tf10_view", kwargs={"id": 1}), view.required_permissions),
    )

    def setUp(self):
        super().setUp()
        self.patched: List[Tuple[str, str]] = []

    def mock_requests_get(self, path):
        expected_prefix = f"{settings.REST_DOMAIN}/api/"
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

        elif path == expected_prefix + "afsender/1":
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

        elif path == expected_prefix + "modtager/1":
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
            }

        elif path == expected_prefix + "afgiftsanmeldelse/1":
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
        elif path == expected_prefix + "fragtforsendelse/1":
            json_content = {
                "id": 1,
                "forsendelsestype": "S",
                "fragtbrevsnummer": 1,
                "fragtbrev": "/leverandørfakturaer/1/leverandørfaktura.txt",
            }

        elif path == expected_prefix + "varelinje":
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

        elif path == expected_prefix + "notat":
            json_content = {
                "count": 1,
                "items": [
                    {
                        "id": 1,
                        "afgiftsanmeldelse": 1,
                        "tekst": "Hephey",
                        "brugernavn": "tester",
                        "oprettet": "2023-10-01T00:00:00.000000+00:00",
                        "index": 0,
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

    def mock_requests_patch(self, path, data, headers=None):
        expected_prefix = f"{settings.REST_DOMAIN}/api/"
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
            reverse("login") + "?back=" + quote(url, safe=""),
        )

    @patch.object(requests.sessions.Session, "get")
    def test_get_view(self, mock_get):
        self.login()
        url = reverse("tf10_view", kwargs={"id": 1})
        mock_get.side_effect = self.mock_requests_get
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    @patch.object(requests.sessions.Session, "get")
    def test_get_view_not_found(self, mock_get):
        self.login()
        url = reverse("tf10_view", kwargs={"id": 2})
        mock_get.side_effect = self.mock_requests_get
        response = self.client.get(url)
        self.assertEquals(response.status_code, 404)

    @patch.object(requests.sessions.Session, "patch")
    def test_post_view_godkend(self, mock_patch):
        self.login()
        view_url = reverse("tf10_view", kwargs={"id": 1})
        mock_patch.side_effect = self.mock_requests_patch
        response = self.client.post(view_url, {"godkendt": "true"})
        self.assertEquals(response.status_code, 302)
        prefix = f"{settings.REST_DOMAIN}/api/"
        patched_map = defaultdict(list)
        for url, data in self.patched:
            patched_map[url].append(json.loads(data))
        self.assertEquals(
            patched_map[prefix + "afgiftsanmeldelse/1"], [{"godkendt": True}]
        )

    @patch.object(requests.sessions.Session, "patch")
    def test_post_view_afvis(self, mock_patch):
        self.login()
        view_url = reverse("tf10_view", kwargs={"id": 1})
        mock_patch.side_effect = self.mock_requests_patch
        response = self.client.post(view_url, {"godkendt": "false"})
        self.assertEquals(response.status_code, 302)
        prefix = f"{settings.REST_DOMAIN}/api/"
        patched_map = defaultdict(list)
        for url, data in self.patched:
            patched_map[url].append(json.loads(data))
        self.assertEquals(
            patched_map[prefix + "afgiftsanmeldelse/1"], [{"godkendt": False}]
        )

    @patch.object(requests.sessions.Session, "patch")
    def test_post_view_not_found(self, mock_patch):
        self.login()
        view_url = reverse("tf10_view", kwargs={"id": 2})
        mock_patch.side_effect = self.mock_requests_patch
        response = self.client.post(view_url, {"godkendt": "true"})
        self.assertEquals(response.status_code, 404)
        prefix = f"{settings.REST_DOMAIN}/api/"
        patched_map = defaultdict(list)
        for url, data in self.patched:
            patched_map[url].append(json.loads(data))
        self.assertEquals(patched_map[prefix + "afgiftsanmeldelse/2"], [])

    @patch.object(requests.sessions.Session, "get")
    def test_get_view_rest_error(self, mock_get):
        self.login()
        url = reverse("tf10_view", kwargs={"id": 1})
        mock_get.side_effect = self.mock_requests_error
        response = self.client.get(url)
        self.assertEquals(response.status_code, 500)

    @patch.object(requests.sessions.Session, "get")
    def test_get_view_rest_error_401(self, mock_get):
        self.login()
        url = reverse("tf10_view", kwargs={"id": 1})
        mock_get.side_effect = self.mock_requests_error_401
        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)

    @patch.object(requests.sessions.Session, "patch")
    def test_post_view_rest_error(self, mock_patch):
        self.login()
        view_url = reverse("tf10_view", kwargs={"id": 1})
        mock_patch.side_effect = self.mock_requests_error
        response = self.client.post(view_url, {"godkendt": "true"})
        self.assertEquals(response.status_code, 500)


class FileViewTest(PermissionsTest, TestCase):
    view = FragtbrevView

    @property
    def login_url(self):
        return str(reverse("login"))

    check_permissions = (
        (reverse("fragtbrev_view", kwargs={"id": 1}), view.required_permissions),
    )

    def mock_requests_get(self, path):
        expected_prefix = f"{settings.REST_DOMAIN}/api/"
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
                "fragtbrev": "/fragtbreve/1/fragtbrev.txt",
            }
        if json_content:
            content = json.dumps(json_content).encode("utf-8")
        if content:
            if not status_code:
                status_code = 200
            response._content = content
        response.status_code = status_code or 404
        return response

    @patch.object(requests.sessions.Session, "get")
    @patch("builtins.open", mock_open(read_data=b"test_data"))
    def test_fileview(self, mock_get):
        self.login()
        url = reverse("fragtbrev_view", kwargs={"id": 1})
        mock_get.side_effect = self.mock_requests_get
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        content = list(response.streaming_content)[0]
        self.assertEquals(content, b"test_data")

    @patch("builtins.open", mock_open(read_data=b"test_data"))
    @patch.object(requests.sessions.Session, "get")
    def test_permissions_admin(self, mock_get):
        super(FileViewTest, self).test_permissions_admin(mock_get)

    @patch("builtins.open", mock_open(read_data=b"test_data"))
    @patch.object(requests.sessions.Session, "get")
    def test_permissions_allowed(self, mock_get):
        super(FileViewTest, self).test_permissions_allowed(mock_get)

    @patch("builtins.open", mock_open(read_data=b"test_data"))
    @patch.object(requests.sessions.Session, "get")
    def test_permissions_disallowed(self, mock_get):
        super(FileViewTest, self).test_permissions_disallowed(mock_get)


class AdminTemplateTagsTest(TemplateTagsTest, TestCase):
    pass


class AdminLoginTest(LoginTest, TestCase):
    @property
    def restricted_url(self):
        return str(reverse("tf10_list"))


class AdminAnmeldelseListViewTest(PermissionsTest, AnmeldelseListViewTest, TestCase):
    can_view = True
    can_edit = False
    can_select_multiple = True
    view = TF10ListView
    check_permissions = ((reverse("tf10_list"), view.required_permissions),)

    @property
    def login_url(self):
        return str(reverse("login"))

    @property
    def list_url(self):
        return str(reverse("tf10_list"))

    def edit_url(self, id):
        return str(reverse("tf10_edit", kwargs={"id": id}))

    def view_url(self, id):
        return str(reverse("tf10_view", kwargs={"id": id}))


class AnmeldelseHistoryListViewTest(PermissionsTest, TestCase):
    view = TF10HistoryListView
    check_permissions = (
        (reverse("tf10_history", kwargs={"id": 1}), view.required_permissions),
    )

    @property
    def login_url(self):
        return str(reverse("login"))

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
                "leverandørfaktura": "/leverand%C3%B8rfakturaer"
                "/10/leverand%C3%B8rfaktura.pdf",
                "afsender": 1,
                "modtager": 1,
                "postforsendelse": 1,
                "dato": "2023-09-03",
                "afgift_total": None,
                "fragtforsendelse": None,
                "godkendt": False,
                "history_username": "admin",
                "history_date": "2023-10-01",
            },
            {
                "id": 1,
                "leverandørfaktura_nummer": "12345",
                "modtager_betaler": False,
                "indførselstilladelse": "abcde",
                "betalt": False,
                "leverandørfaktura": "/leverand%C3%B8rfakturaer"
                "/10/leverand%C3%B8rfaktura.pdf",
                "afsender": 1,
                "modtager": 1,
                "postforsendelse": 1,
                "dato": "2023-09-03",
                "afgift_total": None,
                "fragtforsendelse": None,
                "godkendt": True,
                "history_username": "admin",
                "history_date": "2023-10-02",
            },
        ]

    def mock_requests_get(self, path):
        expected_prefix = "/api/"
        p = urlparse(path)
        path = p.path
        path = path.rstrip("/")
        response = Response()
        json_content = None
        content = None
        status_code = None
        if path == expected_prefix + "afgiftsanmeldelse/1/history":
            items = deepcopy(self.testdata)
            json_content = {"count": len(items), "items": items}
        elif path == expected_prefix + "notat":
            json_content = {"count": 0, "items": []}
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

    @patch.object(requests.sessions.Session, "get")
    def test_list_view(self, mock_get):
        mock_get.side_effect = self.mock_requests_get
        self.login()
        url = reverse("tf10_history", kwargs={"id": 1})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        list_items = self.get_html_list(response.content)
        self.assertEquals(
            list_items,
            [
                {
                    "Dato": "2023-10-01 00:00:00",
                    "Ændret af": "admin",
                    "Notat": "",
                    "Handlinger": "Vis",
                },
                {
                    "Dato": "2023-10-02 00:00:00",
                    "Ændret af": "admin",
                    "Notat": "",
                    "Handlinger": "Vis",
                },
            ],
        )


class AnmeldelseHistoryDetailViewTest(PermissionsTest, TestCase):
    view = TF10HistoryDetailView
    check_permissions = (
        (
            reverse("tf10_history_view", kwargs={"id": 1, "index": 0}),
            view.required_permissions,
        ),
    )

    @property
    def login_url(self):
        return str(reverse("login"))

    def mock_requests_get(self, path):
        expected_prefix = "/api/"
        p = urlparse(path)
        path = p.path
        path = path.rstrip("/")
        response = Response()
        json_content = None
        content = None
        status_code = None
        if path == expected_prefix + "afgiftsanmeldelse/1/history/0":
            json_content = {
                "id": 1,
                "afsender": {
                    "id": 1,
                    "navn": "Testfirma1",
                    "adresse": "Testvej 1",
                    "postnummer": 1234,
                    "by": "Testby",
                    "postbox": None,
                    "telefon": "123456",
                    "cvr": 12345678,
                },
                "modtager": {
                    "id": 2,
                    "navn": "Testfirma2",
                    "adresse": "Testvej 2",
                    "postnummer": 1234,
                    "by": "Testby",
                    "postbox": None,
                    "telefon": "789012",
                    "cvr": 12345679,
                    "kreditordning": False,
                },
                "fragtforsendelse": {
                    "id": 1,
                    "forsendelsestype": "F",
                    "fragtbrevsnummer": "0",
                    "fragtbrev": "/fragtbreve/1/fragtbrev.txt",
                    "forbindelsesnr": "7331",
                },
                "postforsendelse": None,
                "leverandørfaktura_nummer": "1234",
                "leverandørfaktura": "/leverandørfakturaer/1/leverandørfaktura.txt",
                "modtager_betaler": False,
                "indførselstilladelse": "5678",
                "afgift_total": None,
                "betalt": False,
                "dato": "2023-10-06",
                "godkendt": None,
                "history_username": "admin",
                "history_date": "2023-10-01T00:00:00.000000+00:00",
            }
        elif path == expected_prefix + "varelinje":
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
        elif path == expected_prefix + "vareafgiftssats/1":
            json_content = {
                "id": 1,
                "afgiftstabel": 1,
                "vareart": "Båthorn",
                "afgiftsgruppenummer": 1234567,
                "enhed": "kg",
                "afgiftssats": "1.00",
            }
        elif path == expected_prefix + "notat":
            json_content = {
                "count": 1,
                "items": [
                    {
                        "id": 1,
                        "afgiftsanmeldelse": 1,
                        "oprettet": "2023-10-01T00:00:00.000000+00:00",
                        "tekst": "Test tekst",
                        "index": 0,
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

    @patch.object(requests.sessions.Session, "get")
    @patch.object(TemplateView, "get_context_data")
    def test_context_data(self, mock_super_context_data, mock_get):
        mock_get.side_effect = self.mock_requests_get
        self.login()
        try:
            self.client.get(reverse("tf10_history_view", kwargs={"id": 1, "index": 0}))
            mock_super_context_data.assert_called_with(
                {
                    "id": 1,
                    "index": 0,
                    "object": {
                        "id": 1,
                        "afsender": {
                            "id": 1,
                            "navn": "Testfirma1",
                            "adresse": "Testvej 1",
                            "postnummer": 1234,
                            "by": "Testby",
                            "postbox": None,
                            "telefon": "123456",
                            "cvr": 12345678,
                        },
                        "modtager": {
                            "id": 2,
                            "navn": "Testfirma2",
                            "adresse": "Testvej 2",
                            "postnummer": 1234,
                            "by": "Testby",
                            "postbox": None,
                            "telefon": "789012",
                            "cvr": 12345679,
                            "kreditordning": False,
                        },
                        "fragtforsendelse": {
                            "id": 1,
                            "forsendelsestype": "F",
                            "fragtbrevsnummer": "0",
                            "fragtbrev": "/fragtbreve/1/fragtbrev.txt",
                            "forbindelsesnr": "7331",
                        },
                        "postforsendelse": None,
                        "leverandørfaktura_nummer": "1234",
                        "leverandørfaktura": "/leverandørfakturaer/1/leverandørfaktura.txt",
                        "modtager_betaler": False,
                        "indførselstilladelse": "5678",
                        "afgift_total": None,
                        "betalt": False,
                        "dato": "2023-10-06",
                        "godkendt": None,
                        "history_username": "admin",
                        "history_date": "2023-10-01T00:00:00.000000+00:00",
                        "varelinjer": [
                            {
                                "id": 1,
                                "afgiftsanmeldelse": 1,
                                "vareafgiftssats": Vareafgiftssats(
                                    id=1,
                                    afgiftstabel=1,
                                    vareart="Båthorn",
                                    afgiftsgruppenummer=1234567,
                                    enhed=Vareafgiftssats.Enhed.KILOGRAM,
                                    afgiftssats=Decimal("1.00"),
                                    kræver_indførselstilladelse=False,
                                    minimumsbeløb=None,
                                    overordnet=None,
                                    segment_nedre=None,
                                    segment_øvre=None,
                                    subsatser=None,
                                ),
                                "antal": 5,
                                "afgiftsbeløb": "5000.00",
                            }
                        ],
                        "notater": [
                            Notat(
                                id=1,
                                tekst="Test tekst",
                                afgiftsanmeldelse=1,
                                oprettet=datetime.datetime(
                                    2023, 10, 1, 0, 0, tzinfo=datetime.timezone.utc
                                ),
                                brugernavn=None,
                                index=0,
                            )
                        ],
                    },
                    "user": {
                        "username": "admin",
                        "first_name": "Administrator",
                        "last_name": "",
                        "email": "admin@told.gl",
                        "is_superuser": True,
                        "permissions": [
                            "auth.add_group",
                            "auth.change_group",
                            "auth.delete_group",
                            "auth.view_group",
                            "auth.add_permission",
                            "auth.change_permission",
                            "auth.delete_permission",
                            "auth.view_permission",
                            "auth.add_user",
                            "auth.change_user",
                            "auth.delete_user",
                            "auth.view_user",
                            "contenttypes.add_contenttype",
                            "contenttypes.change_contenttype",
                            "contenttypes.delete_contenttype",
                            "contenttypes.view_contenttype",
                            "sessions.add_session",
                            "sessions.change_session",
                            "sessions.delete_session",
                            "sessions.view_session",
                        ],
                    },
                }
            )
        except TypeError:
            pass  # Vi overstyrer TemplateView.get_context_data for at detektere og asserte på dens input,
            # men det betyder at den ikke rigtigt renderer siden. Det er vi dog. p.t. ligeglade med


class AnmeldelseNotatTest(PermissionsTest, TestCase):
    view = TF10FormUpdateView
    check_permissions = (
        (
            reverse("tf10_edit", kwargs={"id": 1}),
            view.required_permissions,
        ),
    )

    def setUp(self):
        super().setUp()
        self.patched: List[Tuple[str, str]] = []
        self.posted: List[Tuple[str, str]] = []

    @staticmethod
    def mock_requests_get(path):
        expected_prefix = f"{settings.REST_DOMAIN}/api/"
        path = path.split("?")[0]
        path = path.rstrip("/")
        response = Response()
        json_content = None
        content = None
        status_code = None
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
        elif path == expected_prefix + "vareafgiftssats/1":
            json_content = {
                "id": 1,
                "afgiftstabel": 1,
                "vareart": "Båthorn",
                "afgiftsgruppenummer": 1234567,
                "enhed": "kg",
                "afgiftssats": "1.00",
            }

        elif path == expected_prefix + "afsender/1":
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
        elif path == expected_prefix + "afsender":
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

        elif path == expected_prefix + "modtager/1":
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
            }

        elif path == expected_prefix + "modtager":
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

        elif path == expected_prefix + "afgiftsanmeldelse/1":
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
        elif path == expected_prefix + "afgiftsanmeldelse/1/full":
            json_content = {
                "id": 1,
                "leverandørfaktura_nummer": "1234",
                "modtager_betaler": False,
                "indførselstilladelse": "abcde",
                "betalt": False,
                "leverandørfaktura": "/leverandørfakturaer/1/leverandørfaktura.txt",
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
                },
                "postforsendelse": {
                    "id": 1,
                    "postforsendelsesnummer": "1234",
                    "forsendelsestype": "S",
                    "afsenderbykode": "2468",
                    "afgangsdato": "2023-11-03",
                },
                "dato": "2023-09-03",
                "afgift_total": None,
                "fragtforsendelse": None,
                "godkendt": False,
            }
        elif path == expected_prefix + "fragtforsendelse/1":
            json_content = {
                "id": 1,
                "forsendelsestype": "S",
                "fragtbrevsnummer": 1,
                "fragtbrev": "/leverandørfakturaer/1/leverandørfaktura.txt",
            }

        elif path == expected_prefix + "varelinje":
            json_content = {
                "count": 1,
                "items": [
                    {
                        "id": 1,
                        "afgiftsanmeldelse": 1,
                        "vareafgiftssats": 1,
                        "antal": 5,
                        "mængde": 2,
                        "fakturabeløb": "25000.00",
                        "afgiftsbeløb": "5000.00",
                    }
                ],
            }

        elif path == expected_prefix + "notat":
            json_content = {
                "count": 1,
                "items": [
                    {
                        "id": 1,
                        "afgiftsanmeldelse": 1,
                        "tekst": "Hephey",
                        "brugernavn": "tester",
                        "oprettet": "2023-10-01T00:00:00.000000+00:00",
                        "index": 0,
                    }
                ],
            }
        elif path == expected_prefix + "afgiftstabel":
            json_content = {
                "count": 1,
                "items": [
                    {
                        "id": 1,
                        "gyldig_fra": "2022-01-01",
                        "gyldig_til": "2023-01-01",
                        "kladde": False,
                    },
                ],
            }
        else:
            print(f"Mock got unrecognized path: {path}")
            traceback.print_stack()
        if json_content:
            content = json.dumps(json_content).encode("utf-8")
        if content:
            if not status_code:
                status_code = 200
            response._content = content
        response.status_code = status_code or 404
        return response

    def mock_requests_patch(self, path, data, headers=None):
        path = path.rstrip("/")
        response = Response()
        content = None
        status_code = None
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

    def mock_requests_post(self, path, data, headers=None):
        path = path.rstrip("/")
        response = Response()
        content = None
        status_code = None
        json_content = {"id": 1}
        self.posted.append((path, data))
        if json_content:
            content = json.dumps(json_content).encode("utf-8")
        if content:
            if not status_code:
                status_code = 200
            response._content = content
        response.status_code = status_code or 404
        return response

    @patch.object(requests.sessions.Session, "get")
    @patch.object(requests.sessions.Session, "patch")
    @patch.object(requests.sessions.Session, "post")
    def test_add_notat(self, mock_post, mock_patch, mock_get):
        self.login()
        mock_get.side_effect = self.mock_requests_get
        mock_patch.side_effect = self.mock_requests_patch
        mock_post.side_effect = self.mock_requests_post
        self.client.post(
            reverse("tf10_edit", kwargs={"id": 1}),
            {
                "afsender_cvr": "12345678",
                "afsender_navn": "Testfirma 5",
                "afsender_adresse": "Testvej 42",
                "afsender_postbox": "123",
                "afsender_postnummer": "1234",
                "afsender_by": "TestBy",
                "afsender_telefon": "123456",
                "modtager_cvr": "12345678",
                "modtager_navn": "Testfirma 3",
                "modtager_adresse": "Testvej 42",
                "modtager_postbox": "123",
                "modtager_postnummer": ["3506"],
                "modtager_by": "TestBy",
                "modtager_telefon": "123456",
                "modtager_indførselstilladelse": "123",
                "leverandørfaktura_nummer": "5678",
                "fragttype": "skibspost",
                "forbindelsesnr": "2468",
                "fragtbrevnr": "1234",
                "afgangsdato": "2023-11-03",
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "1",
                "form-MIN_NUM_FORMS": "1",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-id": 1,
                "form-0-vareafgiftssats": 1,
                "form-0-mængde": 2,
                "form-0-antal": 5,
                "form-0-fakturabeløb": "25000.00",
                "notat": "Testnotat",
            },
        )
        self.assertIn(
            (
                f"{settings.REST_DOMAIN}/api/notat",
                '{"afgiftsanmeldelse_id": 1, "tekst": "Testnotat"}',
            ),
            self.posted,
        )


class AdminFileViewTest(FileViewTest, TestCase):
    @property
    def login_url(self):
        return str(reverse("login"))

    @property
    def file_view_url(self):
        return str(reverse("fragtbrev_view", kwargs={"id": 1}))


class AfgiftstabelListViewTest(PermissionsTest, TestCase):
    @property
    def login_url(self):
        return str(reverse("login"))

    view = AfgiftstabelListView
    check_permissions = ((reverse("afgiftstabel_list"), view.required_permissions),)

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
            self.login_url + "?back=" + quote(url, safe=""),
        )

    @patch.object(requests.sessions.Session, "get")
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
                    "Gyldig til": "-",
                    "Kladde": "Nej",
                    "Handlinger": "Vis Download .xlsx .csv",
                },
                {
                    "Gyldig fra": "-",
                    "Gyldig til": "-",
                    "Kladde": "Ja",
                    "Handlinger": "Vis Download .xlsx .csv",
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
                        "kladde": False,
                        "actions": "Vis Download .xlsx .csv",
                        "gældende": False,
                    },
                    {
                        "id": 2,
                        "gyldig_fra": "2023-01-01",
                        "gyldig_til": None,
                        "kladde": False,
                        "actions": "Vis Download .xlsx .csv",
                        "gældende": True,
                    },
                    {
                        "id": 3,
                        "gyldig_fra": None,
                        "gyldig_til": None,
                        "kladde": True,
                        "actions": "Vis Download .xlsx .csv",
                        "gældende": False,
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

    @patch.object(requests.sessions.Session, "get")
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

    @patch.object(requests.sessions.Session, "get")
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


class AfgiftstabelDownloadTest(PermissionsTest, TestCase):
    @property
    def login_url(self):
        return str(reverse("login"))

    view = AfgiftstabelDownloadView
    check_permissions = (
        (
            reverse("afgiftstabel_download", kwargs={"id": 1, "format": "xlsx"}),
            view.required_permissions,
        ),
        (
            reverse("afgiftstabel_download", kwargs={"id": 1, "format": "csv"}),
            view.required_permissions,
        ),
    )

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

    @patch.object(requests.sessions.Session, "get")
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

    @patch.object(requests.sessions.Session, "get")
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


class AfgiftstabelUploadTest(HasLogin):
    @property
    def login_url(self):
        return str(reverse("login"))

    def setUp(self):
        super().setUp()
        self.posted = []
        self.id_counter = 1

        self.data = [
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
            ["1", "", "SUKKER og sirup", "kilogram", "6,00", "nej", "0,00", "", ""],
            [
                "2",
                "",
                "KAFFE, pulverkaffe, koncentrater",
                "kilogram",
                "6,00",
                "nej",
                "0,00",
                "",
                "",
            ],
            [
                "3",
                "",
                "THE, pulver The, koncentrater",
                "kilogram",
                "6,60",
                "nej",
                "0,00",
                "",
                "",
            ],
        ]

    def mock_requests_post(self, path, data, headers=None):
        expected_prefix = f"{settings.REST_DOMAIN}/api/"
        path = path.rstrip("/")
        response = Response()
        json_content = None
        content = None
        status_code = None
        if path == expected_prefix + "afgiftstabel":
            json_content = {"id": 1}
            self.posted.append((path, data))
        if path == expected_prefix + "vareafgiftssats":
            json_content = {"id": self.id_counter}
            self.id_counter += 1
            self.posted.append((path, data))
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

    @patch.object(requests.sessions.Session, "post")
    def test_successful_upload(self, mock_post):
        mock_post.side_effect = self.mock_requests_post
        response = self.upload(self.data)
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response.headers["Location"], reverse("afgiftstabel_list"))

    @patch.object(requests.sessions.Session, "post")
    def test_failure_wrong_content_type(self, mock_post):
        mock_post.side_effect = self.mock_requests_post
        response = self.upload(self.data, "text/plain")
        self.assertEquals(response.status_code, 200)
        errors = self.get_errors(response.content)
        self.assertTrue("fil" in errors)
        self.assertEquals(errors["fil"], ["Ugyldig content-type: text/plain"])

    @patch.object(requests.sessions.Session, "post")
    def test_failure_header_missing(self, mock_post):
        mock_post.side_effect = self.mock_requests_post
        for i in range(0, 9):
            data = deepcopy(self.data)
            for line in data:
                line.pop(i)
            response = self.upload(data)
            self.assertEquals(response.status_code, 200)
            errors = self.get_errors(response.content)
            self.assertTrue("fil" in errors)
            self.assertEquals(errors["fil"], [f"Mangler kolonne med {self.data[0][i]}"])

    @patch.object(requests.sessions.Session, "post")
    def test_failure_number_twice(self, mock_post):
        mock_post.side_effect = self.mock_requests_post
        self.data[3][0] = "2"
        response = self.upload(self.data)
        self.assertEquals(response.status_code, 200)
        errors = self.get_errors(response.content)
        self.assertTrue("fil" in errors)
        self.assertEquals(
            errors["fil"], ["Afgiftsgruppenummer 2 optræder to gange (linjer: 3, 4)"]
        )

    @patch.object(requests.sessions.Session, "post")
    def test_failure_missing_reference(self, mock_post):
        mock_post.side_effect = self.mock_requests_post
        self.data[3][1] = "4"
        response = self.upload(self.data)
        self.assertEquals(response.status_code, 200)
        errors = self.get_errors(response.content)
        self.assertTrue("fil" in errors)
        self.assertEquals(
            errors["fil"],
            [
                "Afgiftssats med afgiftsgruppenummer 3 (linje 4) peger på overordnet 4, som ikke findes"
            ],
        )

    @patch.object(requests.sessions.Session, "post")
    def test_failure_reference_self(self, mock_post):
        mock_post.side_effect = self.mock_requests_post
        self.data[1][1] = "1"
        response = self.upload(self.data)
        self.assertEquals(response.status_code, 200)
        errors = self.get_errors(response.content)
        self.assertTrue("fil" in errors)
        self.assertEquals(
            errors["fil"],
            ["Vareafgiftssats 1 (linje 2) peger på sig selv som overordnet"],
        )

    @patch.object(requests.sessions.Session, "post")
    def test_failure_circular_reference(self, mock_post):
        mock_post.side_effect = self.mock_requests_post
        self.data[1][1] = "3"
        self.data[2][1] = "1"
        self.data[3][1] = "2"
        response = self.upload(self.data)
        self.assertEquals(response.status_code, 200)
        errors = self.get_errors(response.content)
        self.assertTrue("fil" in errors)
        self.assertEquals(
            errors["fil"],
            [
                "Vareafgiftssats 2 (linje 3) har 1 (linje 2) som overordnet, men 1 har også 2 i kæden af overordnede"
            ],
        )


class AfgiftstabelUploadCsvTest(AfgiftstabelUploadTest, TestCase):
    def upload(self, data: List[List[str]], content_type: str = "text/csv"):
        encoded = "\n".join(
            [",".join([f'"{cell}"' for cell in line]) for line in data]
        ).encode("utf-8")
        self.login()
        return self.client.post(
            reverse("afgiftstabel_create"),
            {"fil": SimpleUploadedFile("test.csv", encoded, content_type)},
        )


class AfgiftstabelUploadXlsxTest(AfgiftstabelUploadTest, TestCase):
    def upload(
        self,
        data: List[List[str]],
        content_type: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ):
        wb = Workbook(write_only=True)
        ws = wb.create_sheet()
        for item in data:
            ws.append(item)
        output = BytesIO()
        wb.save(output)
        encoded = output.getvalue()
        self.login()
        return self.client.post(
            reverse("afgiftstabel_create"),
            {"fil": SimpleUploadedFile("test.xlsx", encoded, content_type)},
        )


class TF10EditMultipleViewTest(PermissionsTest, TestCase):
    view = TF10EditMultipleView
    check_permissions = (
        (reverse("tf10_edit_multiple") + "?id=1", view.required_permissions, 302),
        (reverse("tf10_edit_multiple") + "?id=1&id=2", view.required_permissions),
    )

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
        if path == expected_prefix + "afgiftsanmeldelse":
            data = {
                1: {
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
                },
                2: {
                    "id": 2,
                    "afsender": 1,
                    "modtager": 1,
                    "fragtforsendelse": 2,
                    "postforsendelse": None,
                    "leverandørfaktura_nummer": "1234",
                    "leverandørfaktura": "/leverandørfakturaer/1/leverandørfaktura.txt",
                    "modtager_betaler": False,
                    "indførselstilladelse": "5678",
                    "afgift_total": None,
                    "betalt": False,
                    "dato": "2023-08-22",
                    "godkendt": False,
                },
                3: {
                    "id": 3,
                    "afsender": 1,
                    "modtager": 1,
                    "fragtforsendelse": 3,
                    "postforsendelse": None,
                    "leverandørfaktura_nummer": "1234",
                    "leverandørfaktura": "/leverandørfakturaer/1/leverandørfaktura.txt",
                    "modtager_betaler": False,
                    "indførselstilladelse": "5678",
                    "afgift_total": None,
                    "betalt": False,
                    "dato": "2023-08-22",
                    "godkendt": False,
                },
            }
            items = list(filter(None, [data.get(int(id), None) for id in query["id"]]))
            json_content = {
                "count": len(items),
                "items": items,
            }
        elif path == expected_prefix + "fragtforsendelse/1":
            json_content = {
                "id": 1,
                "forsendelsestype": "S",
                "fragtbrevsnummer": 1,
                "fragtbrev": "/leverandørfakturaer/1/leverandørfaktura.txt",
            }
        elif path == expected_prefix + "fragtforsendelse/2":
            json_content = {
                "id": 2,
                "forsendelsestype": "F",
                "fragtbrevsnummer": 1,
                "fragtbrev": "/leverandørfakturaer/1/leverandørfaktura.txt",
            }
        elif path == expected_prefix + "fragtforsendelse/3":
            json_content = {
                "id": 3,
                "forsendelsestype": "F",
                "fragtbrevsnummer": 1,
                "fragtbrev": "/leverandørfakturaer/1/leverandørfaktura.txt",
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

    def analyze_html(self, html):
        soup = BeautifulSoup(html, "html.parser")
        return {
            "fields": [x.attrs["name"] for x in soup.find_all("input")],
            "disabled_fields": [
                x.attrs["name"] for x in soup.find_all("input", disabled=True)
            ],
            "alerts": [x.text.strip() for x in soup.find_all(class_="alert")],
        }

    def test_get_redirect(self):
        self.login()
        response = self.client.get(reverse("tf10_edit_multiple") + "?id=1")
        self.assertEquals(response.status_code, 302)
        self.assertEquals(
            response.headers["Location"], reverse("tf10_edit", kwargs={"id": 1})
        )

    @patch.object(requests.sessions.Session, "get")
    def test_get_form_diff_fragttype(self, mock_get):
        self.login()
        mock_get.side_effect = self.mock_requests_get
        response = self.client.get(reverse("tf10_edit_multiple") + "?id=1&id=2")
        self.assertEquals(response.status_code, 200)
        analysis = self.analyze_html(response.content)
        self.assertIn("forbindelsesnr", analysis["disabled_fields"])
        self.assertIn(
            "Forbindelsesnummer og fragtbrevnummer kan kun redigeres hvis alle de redigerede afgiftsanmeldelser har samme fragttype.",
            analysis["alerts"],
        )

    @patch.object(requests.sessions.Session, "get")
    def test_get_form_same_fragttype(self, mock_get):
        self.login()
        mock_get.side_effect = self.mock_requests_get
        response = self.client.get(reverse("tf10_edit_multiple") + "?id=2&id=3")
        self.assertEquals(response.status_code, 200)
        analysis = self.analyze_html(response.content)
        self.assertNotIn("forbindelsesnr", analysis["disabled_fields"])
        self.assertNotIn("fragtbrevnr", analysis["disabled_fields"])
        self.assertNotIn(
            "Forbindelsesnummer og fragtbrevnummer kan kun redigeres hvis alle de redigerede afgiftsanmeldelser har samme fragttype.",
            analysis["alerts"],
        )
