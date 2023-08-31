import json
import time
from collections import defaultdict
from datetime import timedelta, datetime
from typing import List, Tuple
from unittest.mock import patch, mock_open
from urllib.parse import quote, quote_plus

import requests
from bs4 import BeautifulSoup
from django.test import TestCase
from django.urls import reverse
from requests import Response
from told_common.rest_client import RestClient
from told_common.tests import TemplateTagsTest


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
                        "afgiftssats": 1,
                        "kvantum": 5,
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


class AdminTemplateTagsTest(TemplateTagsTest):
    pass
