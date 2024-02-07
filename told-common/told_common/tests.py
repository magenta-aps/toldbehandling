# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import json
import os
import time
from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal
from io import StringIO
from typing import Any, Callable, Tuple
from unittest import TestCase
from unittest.mock import mock_open, patch
from urllib.parse import parse_qs, quote, quote_plus, urlparse

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.auth.models import Permission
from django.http import FileResponse
from django.test import override_settings
from django.urls import reverse
from requests import Response
from told_common.data import unformat_decimal
from told_common.rest_client import RestClient
from told_common.templatetags.common_tags import file_basename, zfill
from told_common.views import FileView


class TestMixin:
    @staticmethod
    def get_errors(html: str):
        soup = BeautifulSoup(html, "html.parser")
        error_fields = {}
        for element in soup.find_all(class_="is-invalid"):
            name = element.get("name") or element.get("data-fileinput")
            if name:
                el = element
                for i in range(1, 3):
                    el = el.parent
                    errorlist = el.find(class_="errorlist")
                    if errorlist:
                        error_fields[name] = [
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


class TemplateTagsTest:
    def test_file_basename(self):
        self.assertEquals(file_basename("/path/to/file.txt"), "file.txt")

    def test_zfill(self):
        self.assertEquals(zfill("444", 10), "0000000444")


class LoginTest(TestMixin):
    def restricted_url(self):
        raise NotImplementedError("Implement in subclasses")

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

    def submit_get_errors(self, url, data):
        return self.get_errors(self.client.post(url, data=data).content)

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
    @patch.object(requests.sessions.Session, "get")
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
    @patch.object(requests.sessions.Session, "get")
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

    @patch.object(requests.sessions.Session, "get")
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
            self.assertEquals(response.status_code, 200)
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
        response = self.client.get(self.restricted_url)
        self.assertEquals(response.status_code, 302)
        self.assertEquals(
            response.headers["Location"],
            "/admin/login?back=" + quote_plus(self.restricted_url),
        )
        mock_get.return_value = self.create_response(500, "")
        response = self.client.get(self.restricted_url)
        self.assertEquals(response.status_code, 302)


class HasLogin:
    @property
    def login_url(self):
        raise NotImplementedError

    def login(self, userdata=None):
        session = self.client.session
        if not userdata:
            userdata = {
                "username": "admin",
                "first_name": "Administrator",
                "last_name": "",
                "email": "admin@told.gl",
                "is_superuser": True,
                "permissions": [
                    f"{p.content_type.app_label}.{p.codename}"
                    for p in Permission.objects.all()
                ],
            }
        session.update(
            {
                "access_token": "123456",
                "refresh_token": "abcdef",
                "access_token_timestamp": time.time(),
                "refresh_token_timestamp": time.time(),
                "user": userdata,
                "saml_user": {
                    "cpr": 1234567890,
                    "cvr": 12345678,
                },
            }
        )
        session.save()


class PermissionsTest(HasLogin):
    check_permissions = ()

    def setUp(self):
        super().setUp()
        self.userdata = {}

    def mock_perm_get(self, url):
        expected_prefix = "/api/"
        p = urlparse(url)
        path = p.path
        path = path.rstrip("/")
        response = Response()
        if path == expected_prefix + "user":
            json_content = {"count": 1, "items": [self.userdata]}
            response._content = json.dumps(json_content).encode("utf-8")
            response.status_code = 200
            return response
        else:
            return self.mock_requests_get(url)

    @patch.object(requests.sessions.Session, "get")
    @patch.object(FileView, "get")
    def test_permissions_admin(self, mock_fileview, mock_get, *args):
        self.userdata = {
            "id": 1,
            "username": "admin",
            "first_name": "Administrator",
            "last_name": "",
            "email": "admin@told.gl",
            "is_superuser": True,
            "groups": [],
            "permissions": [
                f"{p.content_type.app_label}.{p.codename}"
                for p in Permission.objects.all()
            ],
            "indberetter_data": {"cpr": 1234567890, "cvr": 12345678},
        }
        self.login(self.userdata)
        mock_get.side_effect = self.mock_perm_get
        mock_fileview.return_value = FileResponse(StringIO("test_data"))
        for item in self.check_permissions:
            url = item[0]
            expected_status = item[2] if len(item) > 2 else 200
            response = self.client.get(url)
            self.assertEquals(
                expected_status,
                response.status_code,
                f"Expected status {expected_status} "
                f"for url {url}, got {response.status_code}",
            )

    @patch.object(requests.sessions.Session, "get")
    @patch.object(FileView, "get")
    def test_permissions_allowed(self, mock_fileview, mock_get, *args):
        self.userdata = {
            "id": 1,
            "username": "allowed_user",
            "first_name": "Allowed",
            "last_name": "User",
            "email": "allowed@told.gl",
            "is_superuser": False,
            "groups": [],
            "permissions": [
                f"{p.content_type.app_label}.{p.codename}"
                for p in Permission.objects.all()
            ],
            "indberetter_data": {"cpr": 1234567890, "cvr": 12345678},
        }
        mock_get.side_effect = self.mock_perm_get
        mock_fileview.return_value = FileResponse(StringIO("test_data"))
        for item in self.check_permissions:
            url = item[0]
            permissions = item[1]
            expected_status = item[2] if len(item) > 2 else 200
            self.userdata["permissions"] = permissions
            self.login(self.userdata)
            response = self.client.get(url)
            self.assertEquals(
                expected_status,
                response.status_code,
                f"Expected status {expected_status} "
                f"for url {url}, got {response.status_code}",
            )

    @patch.object(requests.sessions.Session, "get")
    def test_permissions_disallowed(self, mock_get, *args):
        mock_get.side_effect = self.mock_perm_get
        for item in self.check_permissions:
            url = item[0]
            permissions = item[1]
            self.userdata = {
                "id": 2,
                "username": "disallowed_user",
                "first_name": "disallowed",
                "last_name": "User",
                "email": "disallowed@told.gl",
                "is_superuser": False,
            }
            for p in permissions:
                reduced_permissions = list(filter(lambda x: x != p, permissions))
                self.userdata["permissions"] = reduced_permissions
                self.login(self.userdata)
                response = self.client.get(url)
                self.assertEquals(
                    403,
                    response.status_code,
                    f"Expected status {403} for url {url}, got {response.status_code}",
                )


class AnmeldelseListViewTest(HasLogin):
    can_select_multiple = False

    def list_url(self):
        raise NotImplementedError("Implement in subclasses")

    def edit_url(self, id):
        raise NotImplementedError("Implement in subclasses")

    def view_url(self, id):
        raise NotImplementedError("Implement in subclasses")

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
                "betales_af": "afsender",
                "indførselstilladelse": "abcde",
                "betalt": False,
                "leverandørfaktura": "/leverand%C3%B8rfakturaer"
                "/10/leverand%C3%B8rfaktura.pdf",
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
                    "afgangsdato": "2023-11-03",
                    "afsenderbykode": "1234",
                },
                "dato": "2023-09-03T00:00:00-02:00",
                "beregnet_faktureringsdato": "2023-11-10",
                "afgift_total": None,
                "fragtforsendelse": None,
                "status": "godkendt",
            },
            {
                "id": 2,
                "leverandørfaktura_nummer": "12345",
                "betales_af": "afsender",
                "indførselstilladelse": "abcde",
                "betalt": False,
                "leverandørfaktura": "/leverand%C3%B8rfakturaer"
                "/10/leverand%C3%B8rfaktura.pdf",
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
                    "afgangsdato": "2023-11-03",
                    "afsenderbykode": "1234",
                },
                "dato": "2023-09-02T00:00:00-02:00",
                "beregnet_faktureringsdato": "2023-11-10",
                "afgift_total": None,
                "fragtforsendelse": None,
                "status": "afvist",
            },
            {
                "id": 3,
                "leverandørfaktura_nummer": "12345",
                "betales_af": "afsender",
                "indførselstilladelse": "abcde",
                "betalt": False,
                "leverandørfaktura": "/leverand%C3%B8rfakturaer"
                "/10/leverand%C3%B8rfaktura.pdf",
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
                    "afgangsdato": "2023-11-03",
                    "afsenderbykode": "1234",
                },
                "dato": "2023-09-01T00:00:00-02:00",
                "beregnet_faktureringsdato": "2023-11-10",
                "afgift_total": None,
                "fragtforsendelse": None,
                "status": "ny",
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
        if path == expected_prefix + "user":
            json_content = {
                "username": "admin",
                "first_name": "Administrator",
                "last_name": "",
                "email": "admin@told.gl",
                "is_superuser": True,
            }
        elif path == expected_prefix + "afgiftsanmeldelse/full":
            items = deepcopy(self.testdata)
            if "dato_før" in query:
                items = list(filter(lambda i: i["dato"] < query["dato_før"][0], items))
            if "dato_efter" in query:
                items = list(
                    filter(lambda i: i["dato"] >= query["dato_efter"][0], items)
                )
            if "status" in query:
                items = list(
                    filter(
                        lambda i: i["status"] == query["status"][0],
                        items,
                    )
                )
            if "id" in query:
                items = list(
                    filter(
                        lambda i: i["id"] == int(query["id"][0]),
                        items,
                    )
                )

            if "modtager" in query:
                items = list(
                    filter(
                        lambda i: i["modtager"]["id"] == int(query["modtager"][0]),
                        items,
                    )
                )
            if "afsender" in query:
                items = list(
                    filter(
                        lambda i: i["afsender"]["id"] == int(query["afsender"][0]),
                        items,
                    )
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
            elif sort == ["status"]:
                items.sort(
                    key=lambda x: x["status"],
                    reverse=reverse,
                )

            json_content = {"count": len(items), "items": items}
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

        elif path == expected_prefix + "afgiftstabel":
            json_content = {
                "count": 1,
                "items": [
                    {
                        "id": 1,
                        "gyldig_fra": "2023-01-01T00:00:00-02:00",
                        "gyldig_til": None,
                        "kladde": False,
                    }
                ],
            }

        elif path == expected_prefix + "afsender":
            json_content = {
                "count": 3,
                "items": [
                    {
                        "id": 20,
                        "navn": "Testfirma 5",
                    },
                    {
                        "id": 22,
                        "navn": "Testfirma 4",
                    },
                    {
                        "id": 24,
                        "navn": "Testfirma 6",
                    },
                ],
            }

        elif path == expected_prefix + "modtager":
            json_content = {
                "count": 3,
                "items": [
                    {
                        "id": 21,
                        "navn": "Testfirma 3",
                    },
                    {
                        "id": 23,
                        "navn": "Testfirma 1",
                    },
                    {
                        "id": 25,
                        "navn": "Testfirma 2",
                    },
                ],
            }

        elif path == expected_prefix + "speditør":
            json_content = {
                "count": 1,
                "items": [
                    {
                        "cvr": 12345678,
                        "navn": "TestSpeditør",
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

    @override_settings(LOGIN_BYPASS_ENABLED=False)
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
        expected = [
            {
                "Nummer": "1",
                "Dato": "2023-09-03T00:00:00-02:00",
                "Afsender": "Testfirma 5",
                "Modtager": "Testfirma 3",
                "Status": "Godkendt",
                "Handlinger": "Vis" if self.can_view else "",
            },
            {
                "Nummer": "2",
                "Dato": "2023-09-02T00:00:00-02:00",
                "Afsender": "Testfirma 4",
                "Modtager": "Testfirma 1",
                "Status": "Afvist",
                "Handlinger": "\n".join(
                    filter(
                        None,
                        [
                            "Vis" if self.can_view else None,
                            "Redigér" if self.can_edit else None,
                        ],
                    )
                ),
            },
            {
                "Nummer": "3",
                "Dato": "2023-09-01T00:00:00-02:00",
                "Afsender": "Testfirma 6",
                "Modtager": "Testfirma 2",
                "Status": "Ny",
                "Handlinger": "\n".join(
                    filter(
                        None,
                        [
                            "Vis" if self.can_view else None,
                            "Redigér" if self.can_edit else None,
                        ],
                    )
                ),
            },
        ]
        if self.can_select_multiple:
            expected = [{**item, "": ""} for item in expected]

        self.assertEquals(table_data, expected)

        url = self.list_url + "?json=1"
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        data = response.json()

        def _view_button(id):
            if self.can_view:
                return (
                    f'<a class="btn btn-primary btn-sm m-1" '
                    f'href="{self.view_url(id)}">Vis</a>'
                )

        def _edit_button(id):
            if self.can_edit:
                return (
                    f'<a class="btn btn-primary btn-sm m-1" '
                    f'href="{self.edit_url(id)}">Redigér</a>'
                )

        self.maxDiff = None

        expected = {
            "total": 3,
            "items": [
                {
                    "select": "",
                    "id": 1,
                    "dato": "2023-09-03T00:00:00-02:00",
                    "afsender": {
                        "adresse": "Testvej 42",
                        "by": "TestBy",
                        "cvr": 12345678,
                        "id": 20,
                        "navn": "Testfirma 5",
                        "postbox": "123",
                        "postnummer": 1234,
                        "telefon": "123456",
                    },
                    "modtager": {
                        "adresse": "Testvej 42",
                        "by": "TestBy",
                        "cvr": 12345678,
                        "id": 21,
                        "kreditordning": True,
                        "navn": "Testfirma 3",
                        "postbox": "123",
                        "postnummer": 1234,
                        "telefon": "123456",
                    },
                    "status": "Godkendt",
                    "actions": _view_button(1) or "",
                },
                {
                    "select": "",
                    "id": 2,
                    "dato": "2023-09-02T00:00:00-02:00",
                    "afsender": {
                        "adresse": "Testvej 42",
                        "by": "TestBy",
                        "cvr": 12345678,
                        "id": 22,
                        "navn": "Testfirma 4",
                        "postbox": "123",
                        "postnummer": 1234,
                        "telefon": "123456",
                    },
                    "modtager": {
                        "adresse": "Testvej 42",
                        "by": "TestBy",
                        "cvr": 12345678,
                        "id": 23,
                        "kreditordning": True,
                        "navn": "Testfirma 1",
                        "postbox": "123",
                        "postnummer": 1234,
                        "telefon": "123456",
                    },
                    "status": "Afvist",
                    "actions": "\n".join(
                        filter(
                            None,
                            [
                                _view_button(2),
                                _edit_button(2),
                            ],
                        )
                    ),
                },
                {
                    "select": "",
                    "id": 3,
                    "dato": "2023-09-01T00:00:00-02:00",
                    "afsender": {
                        "adresse": "Testvej 42",
                        "by": "TestBy",
                        "cvr": 12345678,
                        "id": 24,
                        "navn": "Testfirma 6",
                        "postbox": "123",
                        "postnummer": 1234,
                        "telefon": "123456",
                    },
                    "modtager": {
                        "adresse": "Testvej 42",
                        "by": "TestBy",
                        "cvr": 12345678,
                        "id": 25,
                        "kreditordning": True,
                        "navn": "Testfirma 2",
                        "postbox": "123",
                        "postnummer": 1234,
                        "telefon": "123456",
                    },
                    "status": "Ny",
                    "actions": "\n".join(
                        filter(
                            None,
                            [
                                _view_button(3),
                                _edit_button(3),
                            ],
                        )
                    ),
                },
            ],
        }
        if self.can_select_multiple:
            for item in expected["items"]:
                id = item["id"]
                item[
                    "select"
                ] = f'<input type="checkbox" id="select_{id}" name="id" value="{id}"/>'

        self.assertEquals(
            modify_values(data, (str,), lambda s: collapse_newlines(s)), expected
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
            ("status", "", [2, 1, 3]),
            ("status", "asc", [2, 1, 3]),
            ("status", "desc", [3, 1, 2]),
        ]
        for test in sort_tests:
            url = self.list_url + f"?json=1&sort={test[0]}&order={test[1]}"
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
            ("status", "godkendt", {1}),
            ("status", "afvist", {2}),
            ("status", "", {1, 2, 3}),
            ("status", "ny", {3}),
            ("id", "1", {1}),
            ("id", "2", {2}),
            ("afsender", "20", {1}),
            ("afsender", "22", {2}),
            ("modtager", "21", {1}),
            ("modtager", "23", {2}),
        ]
        for field, value, expected in filter_tests:
            url = self.list_url + f"?json=1&{field}={value}"
            response = self.client.get(url)
            self.assertEquals(
                response.status_code,
                200,
                f"Failed for {field}={value}: {response.content}",
            )
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
            url = self.list_url + f"?json=1&offset={offset}&limit={limit}"
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
                url = self.list_url + f"?json=1&{field}={value}"
                response = self.client.get(url)
                self.assertEquals(response.status_code, 400, f"{url}")
                data = response.json()
                self.assertTrue("error" in data)
                self.assertTrue(field in data["error"])

                url = self.list_url + f"?{field}={value}"
                response = self.client.get(url)
                self.assertEquals(response.status_code, 200)
                soup = BeautifulSoup(response.content, "html.parser")
                error_fields = [
                    element["name"] for element in soup.find_all(class_="is-invalid")
                ]
                self.assertEquals(error_fields, [field])


class FileViewTest(HasLogin):
    def file_view_url(self):
        raise NotImplementedError("Implement in subclasses")

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
    @patch.object(os.path, "exists")
    def test_fileview(self, mock_exists, mock_get):
        with patch("builtins.open", mock_open(read_data=b"test_data")):
            self.login()
            url = self.file_view_url
            mock_get.side_effect = self.mock_requests_get
            mock_exists.return_value = True
            response = self.client.get(url)
            self.assertEquals(response.status_code, 200)
            content = list(response.streaming_content)[0]
            self.assertEquals(content, b"test_data")


def modify_values(item: Any, types: Tuple, action: Callable) -> Any:
    t = type(item)
    if t is dict:
        return {key: modify_values(value, types, action) for key, value in item.items()}
    if t is list:
        return [modify_values(value, types, action) for value in item]
    if t in types:
        return action(item)
    return item


def collapse_newlines(value: str):
    new_values = []
    for line in value.split("\n"):
        line = line.strip()
        if line:
            new_values.append(line)
    return "\n".join(new_values)


class TestData(TestCase):
    def test_unformat_decimal(self):
        self.assertEquals(unformat_decimal("1,0"), Decimal("1.0"))
        self.assertEquals(unformat_decimal("1.0"), Decimal("1.0"))
        self.assertEquals(unformat_decimal("1"), Decimal("1"))
        self.assertEquals(unformat_decimal("1.000,00"), Decimal("1000.00"))
