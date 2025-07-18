# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
import datetime
import json
from decimal import Decimal
from io import BytesIO
from unittest.mock import MagicMock, patch

import pandas as pd
from dateutil.tz import tzoffset
from django.core.cache import cache
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from requests import HTTPError, Response
from told_common.data import (
    Afgiftsanmeldelse,
    Afgiftstabel,
    Afsender,
    FragtForsendelse,
    HistoricAfgiftsanmeldelse,
    Modtager,
    Notat,
    PostForsendelse,
    PrivatAfgiftsanmeldelse,
    Toldkategori,
    Vareafgiftssats,
)
from told_common.tests.tests import HasLogin

from admin.views import StatistikView


class BaseTest(HasLogin, TestCase):

    def setUp(self):
        self.rest_client_patcher = patch("told_common.view_mixins.RestClient")
        self.rest_client_mock = MagicMock()

        self.rest_client_class_mock = self.rest_client_patcher.start()
        self.rest_client_class_mock.return_value = self.rest_client_mock

        self.sats1 = Vareafgiftssats(
            id=1,
            afgiftstabel=123,
            vareart_da="Øl",
            vareart_kl="Beer",
            afgiftsgruppenummer=101,
            enhed=Vareafgiftssats.Enhed.LITER,
            afgiftssats=Decimal("1.25"),
            har_privat_tillægsafgift_alkohol=True,
            kræver_indførselstilladelse=True,
            synlig_privat=True,
            minimumsbeløb=Decimal("5.00"),
            overordnet=3,
            segment_nedre=None,
            segment_øvre=None,
            subsatser=[],
        )

        self.sats2 = Vareafgiftssats(
            id=2,
            afgiftstabel=123,
            vareart_da="Sodavand",
            vareart_kl="Soda",
            afgiftsgruppenummer=102,
            enhed=Vareafgiftssats.Enhed.LITER,
            afgiftssats=Decimal("0.80"),
            har_privat_tillægsafgift_alkohol=False,
            kræver_indførselstilladelse=False,
            synlig_privat=False,
            minimumsbeløb=None,
            overordnet=None,
            segment_nedre=Decimal("0.5"),
            segment_øvre=Decimal("1.5"),
            subsatser=[],
        )

        self.sats3 = Vareafgiftssats(
            id=3,
            afgiftstabel=123,
            vareart_da="Spiritus",
            vareart_kl="Spirits",
            afgiftsgruppenummer=103,
            enhed=Vareafgiftssats.Enhed.PROCENT,
            afgiftssats=Decimal("3.75"),
            har_privat_tillægsafgift_alkohol=True,
            kræver_indførselstilladelse=True,
            synlig_privat=True,
            minimumsbeløb=Decimal("10.00"),
            overordnet=None,
            segment_nedre=None,
            segment_øvre=None,
            subsatser=None,
        )

        self.addCleanup(self.rest_client_patcher.stop)
        cache.clear()


class TF10Test(BaseTest):

    def setUp(self):
        super().setUp()
        self.indberetter_data = {"cpr": "0101011234", "cvr": "123456"}

        def get_item(key):
            return {"id": 111, "fragtforsendelse": {"id": 222}}.get(key, None)

        def get_indberetter(k=None):
            if k is None:
                return MagicMock(get=lambda k: {"cvr": "12345678"}[k])
            elif k == "indberetter_data":
                return self.indberetter_data

        self.indberetter_mock = MagicMock()
        self.indberetter_mock.__bool__.return_value = True
        self.indberetter_mock.get.side_effect = get_indberetter

        self.item_mock = MagicMock()
        self.item_mock.status = "kladde"
        self.item_mock.__getitem__.side_effect = get_item
        self.item_mock.afsender = MagicMock(Afsender)
        self.item_mock.afsender.cvr = 1111

        self.item_mock.modtager = MagicMock(Modtager)
        self.item_mock.modtager.id = 1
        self.item_mock.modtager.cvr = None
        self.item_mock.indberetter = self.indberetter_mock
        self.item_mock.toldkategori = "73A"
        self.item_mock.kategori = "73A"
        self.item_mock.kræver_cvr = True
        self.item_mock.betales_af = "afsender"

        self.item_mock.oprettet_af = {"email": "jack@sparrow.sp"}

        self.rest_client_mock.afgiftanmeldelse.get.return_value = self.item_mock

        kategori = Toldkategori(kategori="73A", navn="foo", kræver_cvr=True)
        self.rest_client_mock.toldkategori.list.return_value = [kategori]

        self.prisme_data = {
            "send_til_prisme": True,
            "modtager_stedkode": "001",
            "toldkategori": "73A",
        }
        self.email_data = {
            "send_til_prisme": False,
            "modtager_stedkode": "001",
            "toldkategori": "73A",
            "status": "afvist",
            "notat1": "foo",
        }
        self.url = reverse("tf10_view", kwargs={"id": 1})

    def test_send_to_prisme(self):
        self.login()
        self.client.post(self.url, data=self.prisme_data)
        self.rest_client_mock.prismeresponse.create.assert_called_once()

    def test_send_to_prisme_permission_denied(self):
        self.login(
            userdata_extra={
                "permissions": [
                    "auth.admin",
                    "aktør.view_afsender",
                    "aktør.view_modtager",
                    "sats.view_vareafgiftssats",
                    # "anmeldelse.prisme_afgiftsanmeldelse",
                    "aktør.change_modtager",
                    "forsendelse.view_postforsendelse",
                    "forsendelse.view_fragtforsendelse",
                    "anmeldelse.view_afgiftsanmeldelse",
                    "anmeldelse.view_varelinje",
                    "anmeldelse.change_afgiftsanmeldelse",
                ],
                "is_superuser": False,
            }
        )
        response = self.client.post(self.url, data=self.prisme_data)
        self.rest_client_mock.prismeresponse.create.assert_not_called()
        self.assertEqual(response.status_code, 403)

    def test_send_to_prisme_no_cvr(self):
        self.login()
        self.assertEqual(self.item_mock.modtager.cvr, None)
        self.item_mock.betales_af = "modtager"
        self.client.post(self.url, data=self.prisme_data)
        self.rest_client_mock.prismeresponse.create.assert_not_called()

    @patch("admin.views.log")
    def test_prismeresponse_create_error(self, mock_log):
        self.rest_client_mock.prismeresponse.create.side_effect = ValueError
        self.login()

        self.client.post(self.url, data=self.prisme_data)
        mock_log.error.assert_called()
        self.assertIn("sendt til prisme, men fejlede", mock_log.error.call_args[0][0])

    @patch("admin.views.send_afgiftsanmeldelse")
    @patch("admin.views.log")
    def test_send_afgiftsanmeldelse_no_responses(
        self, mock_log, mock_send_afgiftsanmeldelse
    ):
        self.login()
        mock_send_afgiftsanmeldelse.return_value = []
        self.client.post(self.url, data=self.prisme_data)
        mock_log.error.assert_called()

        self.assertIn("fik ikke noget svar", mock_log.error.call_args[0][0])

    @override_settings(EMAIL_NOTIFICATIONS_ENABLED=True)
    @patch("admin.views.send_email")
    def test_reject_and_send_mail(self, mock_send_email):
        self.login()
        self.client.post(self.url, data=self.email_data)
        self.rest_client_mock.prismeresponse.create.assert_not_called()
        mock_send_email.assert_called_once()

    @patch("admin.views.send_email")
    def test_reject_and_no_notat(self, mock_send_email):
        self.login()
        self.client.post(
            self.url,
            data={
                "send_til_prisme": False,
                "modtager_stedkode": "001",
                "toldkategori": "73A",
                "status": "afvist",
            },
        )
        self.rest_client_mock.prismeresponse.create.assert_not_called()
        mock_send_email.assert_not_called()

    def test_reject_and_no_status(self):
        self.login()
        self.client.post(
            self.url,
            data={
                "send_til_prisme": False,
                "modtager_stedkode": "001",
                "toldkategori": "73A",
                "notat1": "foo",
            },
        )
        self.rest_client_mock.notat.create.assert_called_once()

    def test_reject_and_not_afvist(self):
        self.login()
        self.client.post(
            self.url,
            data={
                "send_til_prisme": False,
                "modtager_stedkode": "001",
                "toldkategori": "73A",
                "status": "ny",
                "notat1": "foo",
            },
        )
        self.rest_client_mock.afgiftanmeldelse.set_status.assert_called_once()

    def test_reject_and_permission_denied(self):
        self.login(
            userdata_extra={
                "permissions": [
                    "auth.admin",
                    "aktør.view_afsender",
                    "aktør.view_modtager",
                    "sats.view_vareafgiftssats",
                    "anmeldelse.prisme_afgiftsanmeldelse",
                    "aktør.change_modtager",
                    "forsendelse.view_postforsendelse",
                    "forsendelse.view_fragtforsendelse",
                    "anmeldelse.view_afgiftsanmeldelse",
                    "anmeldelse.view_varelinje",
                    # "anmeldelse.change_afgiftsanmeldelse",
                ],
                "is_superuser": False,
            }
        )
        response = self.client.post(
            self.url,
            data={
                "send_til_prisme": False,
                "modtager_stedkode": "001",
                "toldkategori": "73A",
                "status": "afvist",
                "notat1": "foo",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_send_to_prisme_http_500_error(self):
        self.login()

        response = Response()
        response.status_code = 500

        self.rest_client_mock.afgiftanmeldelse.set_status.side_effect = HTTPError(
            response=response
        )

        self.client.post(self.url, data=self.email_data)
        self.rest_client_mock.prismeresponse.create.assert_not_called()

    def test_send_to_prisme_http_404_error(self):
        self.login()

        response = Response()
        response.status_code = 404

        self.rest_client_mock.afgiftanmeldelse.set_status.side_effect = HTTPError(
            response=response
        )

        self.client.post(self.url, data=self.email_data)
        self.rest_client_mock.prismeresponse.create.assert_not_called()


class TestTF10HistoryListView(BaseTest):
    def setUp(self):
        super().setUp()

        self.notat1 = Notat(
            id=1,
            tekst="Dette er et testnotat.",
            afgiftsanmeldelse=123,
            privatafgiftsanmeldelse=None,
            index=0,
            oprettet=datetime.datetime.now(),
            navn="Test Bruger",
        )

        self.afgiftanmeldelse1 = HistoricAfgiftsanmeldelse(
            id=1001,
            afsender=1,  # Could also be an instance of Afsender
            modtager=2,  # Or a Modtager object
            fragtforsendelse=3,
            postforsendelse=4,
            leverandørfaktura_nummer="INV-2025-0001",
            leverandørfaktura=None,
            indførselstilladelse="IMPORT-9876",
            afgift_total=Decimal("1234.56"),
            betalt=True,
            status="godkendt",
            dato=datetime.datetime(2025, 7, 1, 14, 30),
            beregnet_faktureringsdato=datetime.date(2025, 7, 10),
            notater=None,
            prismeresponses=None,
            varelinjer=None,
            oprettet_af={"id": 1, "navn": "Testbruger"},
            oprettet_på_vegne_af=None,
            toldkategori="standard",
            fuldmagtshaver=None,
            betales_af="importør",
            tf3=False,
            history_username=None,
            history_date="2025-07-10 09:00",
        )

        self.notater = [
            self.notat1,
        ]

        self.rest_client_mock.notat.list.return_value = self.notater
        self.rest_client_mock.afgiftanmeldelse.list_history.return_value = (
            1,
            [self.afgiftanmeldelse1],
        )

        self.url = reverse("tf10_history", kwargs={"id": 1})

    def test_item_to_json_dict(self):
        self.login()

        response = self.client.get(self.url + "?json=1")
        content = json.loads(response.content)

        self.assertEqual(content["total"], 1)
        self.assertEqual(content["items"][0]["notat"], "Dette er et testnotat.")


class TestTF10EditMultipleView(BaseTest):
    def setUp(self):
        super().setUp()

        self.fragtforsendelse = FragtForsendelse(
            id=3,
            forsendelsestype="F",
            fragtbrevsnummer=1,
            fragtbrev="/leverandørfakturaer/1/leverandørfaktura.txt",
            forbindelsesnr="123",
            afgangsdato=datetime.date(2023, 10, 1),
        )

        self.postforsendelse = PostForsendelse(
            id=4,
            forsendelsestype="P",
            postforsendelsesnummer="POST-2025-001",
            afsenderbykode="AARHUS",
            afgangsdato=datetime.date(2025, 6, 15),
            kladde=False,
        )

        self.anmeldelse_1 = Afgiftsanmeldelse(
            id=1,
            afsender=10,
            modtager=20,
            fragtforsendelse=None,
            postforsendelse=None,
            leverandørfaktura_nummer="FAKT-001",
            leverandørfaktura=None,
            indførselstilladelse="IMP-12345",
            afgift_total=Decimal("1250.00"),
            betalt=True,
            status="godkendt",
            dato=datetime.datetime(2025, 7, 1, 10, 0, 0),
            beregnet_faktureringsdato=datetime.date(2025, 7, 10),
            notater=[],
            prismeresponses=[],
            varelinjer=[],
            oprettet_af={"id": 99, "navn": "System Bruger"},
            oprettet_på_vegne_af=None,
            toldkategori="standard",
            fuldmagtshaver=None,
            betales_af="importør",
            tf3=False,
        )

        self.anmeldelse_2 = Afgiftsanmeldelse(
            id=2,
            afsender=11,
            modtager=21,
            fragtforsendelse=None,
            postforsendelse=None,
            leverandørfaktura_nummer="FAKT-002",
            leverandørfaktura=None,
            indførselstilladelse=None,
            afgift_total=Decimal("987.65"),
            betalt=False,
            status="kladde",
            dato=datetime.datetime(2025, 6, 15, 9, 0, 0),
            beregnet_faktureringsdato=datetime.date(2025, 6, 20),
            notater=[],
            prismeresponses=[],
            varelinjer=[],
            oprettet_af={"id": 100, "navn": "Test Bruger"},
            oprettet_på_vegne_af=None,
            toldkategori="midlertidig",
            fuldmagtshaver=None,
            betales_af="modtager",
            tf3=True,
        )

        self.rest_client_mock.afgiftanmeldelse.list.return_value = (
            2,
            [
                self.anmeldelse_1,
                self.anmeldelse_2,
            ],
        )

    def test_invalid_ids(self):
        self.login()
        response = self.client.get(reverse("tf10_edit_multiple") + "?id=abc&id=2")
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Invalid id value", status_code=400)

    def test_missing_ids(self):
        self.login()
        response = self.client.get(reverse("tf10_edit_multiple"))
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Missing id value", status_code=400)

    def test_edit_postforsendelse_items(self):
        self.login()

        self.anmeldelse_1.postforsendelse = self.postforsendelse
        self.anmeldelse_2.postforsendelse = self.postforsendelse

        data = {"forbindelsesnr": "123", "notat": "foo"}
        response = self.client.post(
            reverse("tf10_edit_multiple") + "?id=1&id=2", data=data
        )

        self.assertEqual(response.status_code, 302)
        self.rest_client_mock.postforsendelse.update.called_once()
        self.rest_client_mock.notat.create.called_once()

    def test_edit_fragtforsendelse_items(self):
        self.login()

        self.anmeldelse_1.fragtforsendelse = self.fragtforsendelse
        self.anmeldelse_2.fragtforsendelse = self.fragtforsendelse

        data = {"forbindelsesnr": "123", "notat": "foo"}
        response = self.client.post(
            reverse("tf10_edit_multiple") + "?id=1&id=2", data=data
        )

        self.assertEqual(response.status_code, 302)
        self.rest_client_mock.fragtforsendelse.update.called_once()
        self.rest_client_mock.notat.create.called_once()


class TestAfgiftstabelDetailView(BaseTest):
    def setUp(self):
        super().setUp()

        self.tabel = Afgiftstabel(
            id=1,
            kladde=True,
            gyldig_fra=datetime.datetime(2025, 1, 1),
            gyldig_til=datetime.datetime(2025, 12, 31),
            vareafgiftssatser=[],
        )

        self.rest_client_mock.afgiftstabel.get.return_value = self.tabel

        self.url = reverse("afgiftstabel_view", kwargs={"id": 1})

    def test_delete(self):
        self.login()
        response = self.client.post(self.url, data={"delete": True})
        self.assertEqual(response.status_code, 302)

        self.rest_client_mock.afgiftstabel.delete.assert_called_once()

    def test_permission_denied(self):
        self.login(
            userdata_extra={
                "permissions": [
                    "auth.admin",
                    "sats.view_afgiftstabel",
                    "sats.view_vareafgiftssats",
                ],
                "is_superuser": False,
            }
        )
        response = self.client.post(self.url, data={"delete": True})
        self.assertEqual(response.status_code, 403)

    def test_kladde(self):
        self.login()
        response = self.client.post(
            self.url,
            data={"gyldig_fra": "02/02/2026 02:00", "offset": 120, "kladde": ""},
        )
        self.assertEqual(response.status_code, 302)

        self.rest_client_mock.afgiftstabel.update.assert_called_with(
            1,
            {
                "kladde": True,
                "gyldig_fra": datetime.datetime(
                    2026, 2, 2, 2, 0, tzinfo=tzoffset("offset", 7200)
                ),
                "offset": 120,
                "delete": False,
            },
        )

    def test_kladde_http_500_error(self):
        self.login()

        response = Response()
        response.status_code = 500

        self.rest_client_mock.afgiftstabel.update.side_effect = HTTPError(
            response=response
        )

        response = self.client.post(
            self.url,
            data={"gyldig_fra": "02/02/2026 02:00", "offset": 120, "kladde": ""},
        )
        self.assertEqual(response.status_code, 500)

    def test_kladde_http_404_error(self):
        self.login()

        response = Response()
        response.status_code = 404

        self.rest_client_mock.afgiftstabel.update.side_effect = HTTPError(
            response=response
        )

        response = self.client.post(
            self.url,
            data={"gyldig_fra": "02/02/2026 02:00", "offset": 120, "kladde": ""},
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn("Afgiftstabel findes ikke", str(response.content))

    def test_get_tabel_http_500_error(self):
        self.login()

        response = Response()
        response.status_code = 500

        self.rest_client_mock.afgiftstabel.get.side_effect = HTTPError(
            response=response
        )

        response = self.client.post(
            self.url,
            data={"gyldig_fra": "02/02/2026 02:00", "offset": 120, "kladde": ""},
        )
        self.assertEqual(response.status_code, 500)

    def test_get_tabel_http_404_error(self):
        self.login()

        response = Response()
        response.status_code = 404

        self.rest_client_mock.afgiftstabel.get.side_effect = HTTPError(
            response=response
        )

        response = self.client.post(
            self.url,
            data={"gyldig_fra": "02/02/2026 02:00", "offset": 120, "kladde": ""},
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn("Afgiftstabel findes ikke", str(response.content))


class TestAfgiftstabelDownloadView(BaseTest):
    def setUp(self):
        super().setUp()

        self.afgiftstabel_mock = MagicMock()
        self.afgiftstabel_mock.kladde = True
        self.afgiftstabel_mock.gyldig_fra = "2001"
        self.afgiftstabel_mock.gyldig_til = "2002"

        self.rest_client_mock.afgiftstabel.get.return_value = self.afgiftstabel_mock

        self.rest_client_mock.vareafgiftssats.list.return_value = [
            self.sats1,
            self.sats2,
            self.sats3,
        ]

        self.csv_url = reverse(
            "afgiftstabel_download", kwargs={"id": 1, "format": "csv"}
        )
        self.xlsx_url = reverse(
            "afgiftstabel_download", kwargs={"id": 1, "format": "xlsx"}
        )

    def test_get_csv(self):
        self.login()
        response = self.client.get(self.csv_url)

        df = pd.read_csv(BytesIO(response.content), index_col="Afgiftsgruppenummer")
        self.assertEqual(df.loc[101, "Vareart (da)"], "Øl")
        self.assertEqual(df.loc[102, "Vareart (da)"], "Sodavand")
        self.assertEqual(df.loc[103, "Vareart (da)"], "Spiritus")

    def test_get_xlsx(self):
        self.login()
        response = self.client.get(self.xlsx_url)

        df = pd.read_excel(BytesIO(response.content), index_col="Afgiftsgruppenummer")

        self.assertEqual(df.loc[101, "Vareart (da)"], "Øl")
        self.assertEqual(df.loc[102, "Vareart (da)"], "Sodavand")
        self.assertEqual(df.loc[103, "Vareart (da)"], "Spiritus")

    def test_invalid_format(self):
        self.login()
        response = self.client.get(
            reverse("afgiftstabel_download", kwargs={"id": 1, "format": "xls"})
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Ugyldigt format", str(response.content))

    def test_filename(self):
        self.login()

        response = self.client.get(self.csv_url)
        self.assertIn(
            "Afgiftstabel_kladde.csv", response.headers["Content-Disposition"]
        )

        self.afgiftstabel_mock.kladde = False

        response = self.client.get(self.csv_url)
        self.assertIn(
            "Afgiftstabel_2001_2002.csv", response.headers["Content-Disposition"]
        )

        self.afgiftstabel_mock.gyldig_til = None

        response = self.client.get(self.csv_url)
        self.assertIn(
            "Afgiftstabel_2001_altid.csv", response.headers["Content-Disposition"]
        )

    def test_save(self):
        url = reverse("afgiftstabel_create")
        self.login()

        self.rest_client_mock.afgiftstabel.create.return_value = 1
        self.rest_client_mock.vareafgiftssats.create.return_value = 2

        response = self.client.post(
            url,
            data={
                "fil": SimpleUploadedFile(
                    "test.csv",
                    self.client.get(self.csv_url).content,
                    content_type="text/csv",
                )
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.rest_client_mock.vareafgiftssats.create.call_count, 3)


class TestTF5Views(BaseTest):
    def setUp(self):
        super().setUp()

        self.item1 = PrivatAfgiftsanmeldelse(
            id=1,
            cpr=1234567890,
            anonym=False,
            navn="Anna Andersen",
            adresse="Fiktivvej 1",
            postnummer=2100,
            by="København",
            telefon="12345678",
            leverandørfaktura_nummer="INV001",
            leverandørfaktura=MagicMock(spec=File),  # mocked File object
            bookingnummer="BK001",
            status="oprettet",
            indleveringsdato=datetime.date(2025, 7, 1),
            oprettet=datetime.datetime(2025, 7, 1, 12, 0),
            oprettet_af={"id": 1, "navn": "Admin"},
            payment_status="afventende",
            indførselstilladelse="ABC123",
            varelinjer=[],
            notater=[],
        )

        self.item2 = PrivatAfgiftsanmeldelse(
            id=2,
            cpr=9876543210,
            anonym=True,
            navn="",
            adresse="Hemmeligvej 42",
            postnummer=8000,
            by="Aarhus",
            telefon="87654321",
            leverandørfaktura_nummer="INV002",
            leverandørfaktura=MagicMock(spec=File),  # mocked File object
            bookingnummer="BK002",
            status="afsluttet",
            indleveringsdato=datetime.date(2025, 7, 2),
            oprettet=datetime.datetime(2025, 7, 2, 9, 30),
            oprettet_af={"id": 2, "navn": "System"},
            payment_status="betalt",
            indførselstilladelse=None,
            varelinjer=None,
            notater=None,
        )

        items = [self.item1, self.item2]

        self.rest_client_mock.privat_afgiftsanmeldelse.list.return_value = (2, items)
        self.rest_client_mock.privat_afgiftsanmeldelse.get.return_value = self.item1

    def test_listview(self):
        self.login()
        response = self.client.get(reverse("tf5_list"))

        self.assertEqual(len(response.context_data["items"]), 2)
        self.assertEqual(response.context_data["items"][0]["id"], 1)
        self.assertEqual(response.context_data["items"][1]["id"], 2)

    def test_tf5_view_create_payment(self):
        self.login()
        response = self.client.post(
            reverse("tf5_view", kwargs={"id": 1}), data={"betalt": True}
        )
        self.assertEqual(response.status_code, 302)
        self.rest_client_mock.payment.create.assert_called_once()

    def test_tf5_view_create_payment_permission_denied(self):
        self.login(
            userdata_extra={
                "permissions": [
                    "auth.admin",
                    "anmeldelse.view_privatafgiftsanmeldelse",
                    "payment.add_payment",
                    "payment.add_item",
                    "payment.bank_payment",
                ],
                "is_superuser": False,
            }
        )
        response = self.client.post(
            reverse("tf5_view", kwargs={"id": 1}), data={"betalt": True}
        )
        self.assertEqual(response.status_code, 403)
        self.rest_client_mock.payment.create.assert_not_called()


class TestStatistikView(BaseTest):
    def setUp(self):
        super().setUp()

        self.url = reverse("statistik")

        self.data = {
            "anmeldelsestype": "tf5",
            "startdato": "2024-01-01",
            "slutdato": "2024-12-31",
            "download": True,
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-gruppe": "101,102",
        }

        self.rest_client_mock.vareafgiftssats.list.return_value = [
            self.sats1,
            self.sats2,
        ]

        stats = {
            "count": 4,
            "items": [
                {
                    "afgiftsgruppenummer": 101,
                    "vareart_da": "Chokolade",
                    "vareart_kl": "CHOCO",
                    "enhed": "kg",
                    "sum_afgiftsbeløb": Decimal("12500.00"),
                    "sum_mængde": Decimal("500.00"),
                    "sum_antal": 100,
                },
                {
                    "afgiftsgruppenummer": 102,
                    "vareart_da": "Vin",
                    "vareart_kl": "WINE",
                    "enhed": "l",
                    "sum_afgiftsbeløb": Decimal("8100.00"),
                    "sum_mængde": Decimal("270.00"),
                    "sum_antal": 0,
                },
                {
                    "afgiftsgruppenummer": 103,
                    "vareart_da": "Spiritus",
                    "vareart_kl": "LIQUOR",
                    "enhed": "l",
                    "sum_afgiftsbeløb": Decimal("0.00"),
                    "sum_mængde": Decimal("120.00"),
                    "sum_antal": 0,
                },
                {
                    "afgiftsgruppenummer": 104,
                    "vareart_da": "Energidrik",
                    "vareart_kl": "ENERGY",
                    "enhed": "l",
                    "sum_afgiftsbeløb": Decimal("100.00"),
                    "sum_mængde": Decimal("0.00"),
                    "sum_antal": 0,
                },
                {
                    "afgiftsgruppenummer": 105,
                    "vareart_da": "Lego",
                    "vareart_kl": "LEGO",
                    "enhed": "ant",
                    "sum_afgiftsbeløb": Decimal("100.00"),
                    "sum_mængde": Decimal("0.00"),
                    "sum_antal": 42,
                },
                {
                    "afgiftsgruppenummer": 106,
                    "vareart_da": "Tang",
                    "vareart_kl": "TANG",
                    "enhed": "pct",
                    "sum_afgiftsbeløb": Decimal("100.00"),
                    "sum_mængde": Decimal("0.00"),
                    "sum_antal": 0,
                },
            ],
        }

        self.rest_client_mock.statistik.list.return_value = stats

    def test_get_statistics(self):
        self.login()
        response = self.client.post(self.url, data=self.data)
        df = pd.read_excel(BytesIO(response.content), index_col="AFGIFTGRP")

        self.assertEqual(df.loc[102, "GRUPPE"], "101+102")
        self.assertEqual(df.loc[102, "GRUPPESUM"], 20600)
        self.assertEqual(df.loc[103, "KVANTUM"], 120)
        self.assertEqual(df.loc[104, "AFGIFT"], 100)
