import json
from collections import defaultdict
from typing import List, Tuple
from unittest.mock import patch
from urllib.parse import quote

import requests
from django.test import TestCase
from django.urls import reverse
from requests import Response
from told_common.tests import (
    TemplateTagsTest,
    LoginTest,
    AnmeldelseListViewTest,
    FileViewTest,
    HasLogin,
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
