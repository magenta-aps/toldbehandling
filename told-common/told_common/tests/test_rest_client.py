import base64
import time
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.core.exceptions import ObjectDoesNotExist
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from requests import HTTPError, Response
from told_common.data import Forsendelsestype
from told_common.rest_client import (
    AfgiftanmeldelseRestClient,
    AfgiftstabelRestClient,
    AfsenderRestClient,
    EboksBeskedRestClient,
    FragtforsendelseRestClient,
    JwtTokenInfo,
    ModtagerRestClient,
    NotatRestClient,
    PaymentRestClient,
    PostforsendelseRestClient,
    PrismeResponse,
    PrismeResponseRestClient,
    PrivatAfgiftanmeldelseRestClient,
    RestClient,
    RestClientException,
    TotpDeviceRestClient,
    UserRestClient,
    Vareafgiftssats,
    VareafgiftssatsRestClient,
    VarelinjeRestClient,
)


class RestClientExceptionTests(TestCase):
    def test_str_representation(self):
        exc = RestClientException(status_code=404, content="Not Found")
        expected = (
            "Failure in REST API request; got http 404 from API. Response: Not Found"
        )
        self.assertEqual(str(exc), expected)


class AfsenderRestClientTests(TestCase):
    def setUp(self):
        self.mock_rest = MagicMock()
        self.mock_rest.get.return_value = {"count": 1, "items": [{"id": 42}]}
        self.client = AfsenderRestClient(rest=self.mock_rest)

    def test_get_or_create_existing(self):
        ident = {"navn": "Test Afsender"}
        result = self.client.get_or_create(ident)
        self.assertEqual(result, 42)
        self.mock_rest.get.assert_called_once()

    def test_update(self):
        self.client.update(1, {"data": 123})
        self.mock_rest.patch.assert_called_once()


class ModtagerRestClientTests(TestCase):

    def setUp(self):
        self.mock_rest = MagicMock()
        self.client = ModtagerRestClient(rest=self.mock_rest)

    def test_get_or_create_existing(self):
        self.mock_rest.get.return_value = {"count": 1, "items": [{"id": 123}]}
        ident = {"navn": "Test Modtager"}
        result = self.client.get_or_create(ident)
        self.assertEqual(result, 123)

    def test_update(self):
        result = self.client.update(123, {"modtager_navn": "Updated"})
        self.assertEqual(result, 123)
        self.mock_rest.patch.assert_called_once()


class PostforsendelseRestClientTests(TestCase):
    def setUp(self):
        self.mock_rest = MagicMock()
        self.client = PostforsendelseRestClient(rest=self.mock_rest)

    def test_update_deletes_when_mapped_is_none(self):
        data = {"fragttype": "anden"}  # triggers map() == None
        self.client.update(1, data)
        self.mock_rest.delete.assert_called_with("postforsendelse/1")

    def test_update_skips_when_compare_returns_true(self):
        data = {
            "fragttype": "luftpost",
            "fragtbrevnr": "123",
            "forbindelsesnr": "A",
            "afgangsdato": "2024-01-01",
        }
        existing = {
            "forsendelsestype": "F",
            "postforsendelsesnummer": "123",
            "afsenderbykode": "A",
            "afgangsdato": "2024-01-01",
        }
        self.client.update(5, data, existing)
        self.mock_rest.patch.assert_not_called()

    def test_update_calls_patch_when_different(self):
        data = {
            "fragttype": "skibspost",
            "fragtbrevnr": "NEW",
            "forbindelsesnr": "X",
            "afgangsdato": "2024-02-01",
        }
        existing = {
            "forsendelsestype": "S",
            "postforsendelsesnummer": "OLD",
            "afsenderbykode": "Y",
            "afgangsdato": "2024-01-01",
        }
        self.client.update(9, data, existing)
        self.mock_rest.patch.assert_called_once()

    def test_compare(self):

        data = {
            "forsendelsestype": "S",
            "postforsendelsesnummer": "X",
            "afsenderbykode": "FF",
            "afgangsdato": "2024-02-01",
        }

        self.assertTrue(self.client.compare(data, data))

    def test_get(self):
        self.mock_rest.get.return_value = {
            "forsendelsestype": "S",
            "postforsendelsesnummer": "OLD",
            "afsenderbykode": "Y",
            "afgangsdato": "2024-01-01",
            "id": 1,
        }

        postforsendelse = self.client.get(1)

        self.assertEqual(postforsendelse.id, 1)
        self.assertEqual(postforsendelse.afsenderbykode, "Y")
        self.assertEqual(postforsendelse.forsendelsestype, Forsendelsestype.SKIB)


class FragtforsendelseRestClientTests(TestCase):
    def setUp(self):
        self.mock_rest = MagicMock()
        self.client = FragtforsendelseRestClient(rest=self.mock_rest)

    def test_update_deletes_when_map_returns_none(self):
        data = {"fragttype": "anden"}
        self.client.update(10, data)
        self.mock_rest.delete.assert_called_with("fragtforsendelse/10")

    def test_update_skips_if_same(self):
        data = {
            "fragttype": "luftfragt",
            "fragtbrevnr": "123",
            "forbindelsesnr": "A",
            "afgangsdato": "2024-01-01",
            "fragtbrev": "brev.txt",
        }
        existing = {
            "forsendelsestype": "F",
            "fragtbrevsnummer": "123",
            "forbindelsesnr": "A",
            "afgangsdato": "2024-01-01",
            "fragtbrev": "brev.txt",
        }
        self.client.update(20, data, existing=existing)
        self.mock_rest.patch.assert_not_called()

    def test_update_skips_if_fragtbrev_not_changed(self):
        data = {
            "fragttype": "luftfragt",
            "fragtbrevnr": "123",
            "forbindelsesnr": "A",
            "afgangsdato": "2024-01-01",
        }
        existing = {
            "forsendelsestype": "F",
            "fragtbrevsnummer": "123",
            "forbindelsesnr": "A",
            "afgangsdato": "2024-01-01",
        }
        self.client.update(20, data, existing=existing)
        self.mock_rest.patch.assert_not_called()

    def test_update_patches_if_different(self):
        data = {
            "fragttype": "skibsfragt",
            "fragtbrevnr": "NEW",
            "forbindelsesnr": "X",
            "afgangsdato": "2024-02-01",
        }
        existing = {
            "forsendelsestype": "S",
            "fragtbrevsnummer": "OLD",
            "forbindelsesnr": "Y",
            "afgangsdato": "2024-01-01",
        }
        file = SimpleUploadedFile("test.pdf", b"pdfcontent")
        self.client.update(30, data, file=file, existing=existing)
        self.mock_rest.patch.assert_called_once()

    def test_get_sets_file_and_returns_object(self):
        self.mock_rest.get.return_value = {"id": 1, "fragtbrev": "file.pdf"}
        with patch(
            "told_common.rest_client.FragtForsendelse.from_dict"
        ) as mock_from_dict:
            self.client.get(1)
            self.mock_rest.get.assert_called_with("fragtforsendelse/1")
            mock_from_dict.assert_called_once()

    def test_compare(self):
        data = {
            "forsendelsestype": "S",
            "fragtbrevsnummer": 444,
            "forbindelsesnr": 123,
            "afgangsdato": "2024-02-01",
        }
        self.assertTrue(self.client.compare(data, data))

        data["fragtbrev"] = "brev.txt"
        self.assertFalse(self.client.compare(data, data))

        existing = {
            "forsendelsestype": "S",
            "fragtbrevsnummer": 555,
            "forbindelsesnr": 123,
            "afgangsdato": "2024-02-01",
        }
        self.assertFalse(self.client.compare(data, existing))


class AfgiftanmeldelseRestClientTests(TestCase):
    def setUp(self):
        self.mock_rest = MagicMock()
        self.client = AfgiftanmeldelseRestClient(self.mock_rest)

        self.item = {
            "id": 1,
            "leverandørfaktura_nummer": "123",
            "afsender": MagicMock(),
            "modtager": MagicMock(),
            "postforsendelse": MagicMock(),
            "fragtforsendelse": MagicMock(),
            "indførselstilladelse": "123",
            "afgift_total": 123,
            "betalt": False,
            "status": "OK",
            "dato": "2024-01-01",
            "beregnet_faktureringsdato": "2024-01-01",
        }

    def test_compare_false_if_faktura_exists(self):
        result = self.client.compare({"leverandørfaktura": "yes"}, {})
        self.assertFalse(result)

    def test_compare_false_if_faktura_nummer_differs(self):
        result = self.client.compare(
            {"leverandørfaktura_nummer": "X"}, {"leverandørfaktura_nummer": "Y"}
        )
        self.assertFalse(result)

    def test_compare_false_if_ids_differ(self):
        result = self.client.compare(
            {
                "afsender_id": 1,
                "modtager_id": 2,
                "postforsendelse_id": 3,
                "fragtforsendelse_id": 4,
            },
            {
                "afsender": {"id": 11},
                "modtager": {"id": 2},
                "postforsendelse": {"id": 3},
                "fragtforsendelse": {"id": 4},
            },
        )
        self.assertFalse(result)

    def test_compare_true_if_all_match(self):
        result = self.client.compare(
            {
                "leverandørfaktura": None,
                "leverandørfaktura_nummer": "123",
                "afsender_id": 1,
                "modtager_id": 2,
                "postforsendelse_id": 3,
                "fragtforsendelse_id": 4,
            },
            {
                "leverandørfaktura_nummer": "123",
                "afsender": {"id": 1},
                "modtager": {"id": 2},
                "postforsendelse": {"id": 3},
                "fragtforsendelse": {"id": 4},
            },
        )
        self.assertTrue(result)

    def test_list(self):
        self.mock_rest.get.return_value = {"items": [self.item], "count": 1}
        data = self.client.list()
        item = data[1][0]

        self.assertEqual(data[0], 1)
        self.assertEqual(item.id, 1)
        self.assertTrue(item.varelinjer is None)
        self.assertTrue(item.notater is None)
        self.assertTrue(item.prismeresponses is None)

        args, kwargs = self.mock_rest.get.call_args
        self.assertEqual(args[0], "afgiftsanmeldelse")
        self.mock_rest.get.assert_called_once()

    def test_list_full(self):
        self.mock_rest.get.return_value = {"items": [self.item], "count": 1}
        data = self.client.list(
            full=True,
            include_varelinjer=True,
            include_notater=True,
            include_prismeresponses=True,
        )
        item = data[1][0]

        self.assertEqual(data[0], 1)
        self.assertEqual(item.id, 1)
        self.assertTrue(item.varelinjer is not None)
        self.assertTrue(item.notater is not None)
        self.assertTrue(item.prismeresponses is not None)

        args, kwargs = self.mock_rest.get.call_args
        self.assertEqual(args[0], "afgiftsanmeldelse/full")
        self.mock_rest.get.assert_called_once()

    def test_get_full(self):
        self.mock_rest.get.return_value = self.item

        item = self.client.get(
            1,
            full=True,
            include_varelinjer=True,
            include_notater=True,
            include_prismeresponses=True,
        )

        args, kwargs = self.mock_rest.get.call_args
        self.assertEqual(args[0], "afgiftsanmeldelse/1/full")
        self.mock_rest.get.assert_called_once()

        self.assertEqual(item.id, 1)
        self.assertTrue(item.varelinjer is not None)
        self.assertTrue(item.notater is not None)
        self.assertTrue(item.prismeresponses is not None)

    def test_get(self):
        self.mock_rest.get.return_value = self.item

        item = self.client.get(1)

        args, kwargs = self.mock_rest.get.call_args
        self.assertEqual(args[0], "afgiftsanmeldelse/1")
        self.mock_rest.get.assert_called_once()

        self.assertEqual(item.id, 1)
        self.assertTrue(item.varelinjer is None)
        self.assertTrue(item.notater is None)
        self.assertTrue(item.prismeresponses is None)

    def test_delete(self):
        self.client.delete(1)
        self.mock_rest.delete.assert_called_once()


class AfgiftanmeldelseRestClientUpdateTests(TestCase):
    def setUp(self):
        self.mock_rest = MagicMock()
        self.client = AfgiftanmeldelseRestClient(self.mock_rest)

    def test_update_skips_if_no_force_and_compare_true(self):
        self.client.compare = MagicMock(return_value=True)
        self.client.map = MagicMock(return_value={"leverandørfaktura": None})
        self.client.update(id=1, data={}, existing={"id": 1}, force_write=False)
        self.mock_rest.patch.assert_not_called()

    def test_update_does_patch_if_force_true(self):
        self.client.compare = MagicMock(return_value=True)
        self.client.map = MagicMock(
            return_value={
                "leverandørfaktura": "abc",
                "leverandørfaktura_navn": "test.pdf",
            }
        )
        self.client.update(id=2, data={}, existing={"id": 2}, force_write=True)
        self.mock_rest.patch.assert_called_once()

    def test_update_does_patch_if_compare_false(self):
        self.client.compare = MagicMock(return_value=False)
        self.client.map = MagicMock(
            return_value={
                "leverandørfaktura": "abc",
                "leverandørfaktura_navn": "name.pdf",
            }
        )
        self.client.update(id=3, data={}, existing={"id": 3})
        self.mock_rest.patch.assert_called_once()

    def test_set_status_valid(self):
        for status in ["ny", "godkendt", "afvist"]:
            self.mock_rest.reset_mock()
            self.client.set_status(1, status)
            self.mock_rest.patch.assert_called_with(
                "afgiftsanmeldelse/1", {"status": status}
            )

    def test_set_status_invalid_raises(self):
        with self.assertRaises(Exception) as ctx:
            self.client.set_status(1, "invalid")
        self.assertIn("status skal være", str(ctx.exception))

    def test_set_toldkategori(self):
        self.client.set_toldkategori(99, "foo")
        self.mock_rest.patch.assert_called_with(
            "afgiftsanmeldelse/99", {"toldkategori": "foo"}
        )

    def test_get_full_sets_file_and_calls_lists(self):
        self.mock_rest.get.return_value = {"id": 1, "fragtforsendelse": {"id": 2}}
        self.mock_rest.varelinje.list.return_value = []
        self.mock_rest.notat.list.return_value = []
        self.mock_rest.prismeresponse.list.return_value = []

        with patch(
            "told_common.rest_client.Afgiftsanmeldelse.from_dict"
        ) as mock_from_dict:
            self.client.get(
                id=1,
                full=True,
                include_varelinjer=True,
                include_notater=True,
                include_prismeresponses=True,
            )
            self.assertTrue(mock_from_dict.called)


class PrivatAfgiftanmeldelseRestClientTests(TestCase):
    def setUp(self):
        self.mock_rest = MagicMock()
        self.client = PrivatAfgiftanmeldelseRestClient(self.mock_rest)

        self.item = {
            "cpr": "0101011234",
            "anonym": True,
            "navn": "Bear Grills",
            "adresse": "Himalayas",
            "postnummer": "1234",
            "by": "Sherpa station",
            "telefon": "+45 11 11 11 11",
            "leverandørfaktura_nummer": "123",
            "leverandørfaktura": MagicMock(),
            "bookingnummer": "123",
            "status": "OK",
            "indleveringsdato": "2024-01-01",
            "oprettet": "2024-01-01",
            "oprettet_af": MagicMock(),
            "payment_status": "OK",
            "id": 123,
        }

    def test_list(self):
        self.mock_rest.get.return_value = {"items": [self.item], "count": 1}
        self.client.set_file = MagicMock()
        data = self.client.list(include_varelinjer=True, include_notater=True)

        item = data[1][0]

        self.assertEqual(data[0], 1)
        self.assertEqual(item.id, 123)
        self.assertTrue(item.varelinjer is not None)
        self.assertTrue(item.notater is not None)

    def test_compare_false_if_invoice_present(self):
        result = self.client.compare({"leverandørfaktura": "yes"}, {})
        self.assertFalse(result)

    def test_compare_false_if_invoice_number_differs(self):
        result = self.client.compare(
            {"leverandørfaktura_nummer": "1"}, {"leverandørfaktura_nummer": "2"}
        )
        self.assertFalse(result)

    def test_compare_true_if_all_match(self):
        result = self.client.compare(
            {"leverandørfaktura_nummer": "123"}, {"leverandørfaktura_nummer": "123"}
        )
        self.assertTrue(result)

    def test_get_sets_file_and_returns_object(self):
        self.mock_rest.get.return_value = {"id": 1, "leverandørfaktura": "some.pdf"}
        with patch(
            "told_common.rest_client.PrivatAfgiftsanmeldelse.from_dict"
        ) as mock_from_dict:
            self.client.get(1)
            self.mock_rest.get.assert_called_with("privat_afgiftsanmeldelse/1")
            mock_from_dict.assert_called_once()

    def test_annuller_sets_status_to_annulleret(self):
        self.client.annuller(42)
        self.mock_rest.patch.assert_called_with(
            "privat_afgiftsanmeldelse/42", {"status": "annulleret"}
        )


class VarelinjeRestClientTests(TestCase):

    def setUp(self):
        self.mock_rest = MagicMock()
        self.client = VarelinjeRestClient(self.mock_rest)

    def test_map_raises_if_no_ids(self):
        with self.assertRaises(Exception) as ctx:
            self.client.map(data={})
        self.assertIn("Skal specificere", str(ctx.exception))

    def test_compare_false_on_mismatch(self):
        data = {"fakturabeløb": "100", "vareafgiftssats_id": 1, "antal": 2, "mængde": 3}
        existing = {
            "fakturabeløb": "200",
            "vareafgiftssats_id": 1,
            "antal": 2,
            "mængde": 3,
        }
        result = self.client.compare(data, existing)
        self.assertFalse(result)

    def test_compare_true_if_all_match(self):
        data = {"fakturabeløb": "100", "vareafgiftssats_id": 1, "antal": 2, "mængde": 3}
        existing = {
            "fakturabeløb": "100",
            "vareafgiftssats_id": 1,
            "antal": 2,
            "mængde": 3,
        }
        result = self.client.compare(data, existing)
        self.assertTrue(result)

    def test_delete(self):
        self.client.delete(1)
        self.mock_rest.delete.assert_called_once()


class NotatRestClientTests(TestCase):

    def setUp(self):
        self.mock_rest = MagicMock()
        self.client = NotatRestClient(self.mock_rest)

    def test_map_raises_if_missing_ids(self):
        with self.assertRaises(Exception) as ctx:
            NotatRestClient.map(data={"tekst": "note"})
        self.assertIn("Skal specificere enten", str(ctx.exception))

    def test_create_calls_post(self):
        data = {"tekst": "note"}
        self.client.create(data, afgiftsanmeldelse_id=1)
        self.mock_rest.post.assert_called()

    def test_delete(self):
        self.client.delete(1)
        self.mock_rest.delete.assert_called_once()


class PrismeResponseRestClientTests(TestCase):

    def setUp(self):
        self.mock_rest = MagicMock()
        self.client = PrismeResponseRestClient(self.mock_rest)

    def test_map_with_instance(self):
        response = PrismeResponse(
            afgiftsanmeldelse=1,
            delivery_date="2024-01-01",
            rec_id="ABC",
            tax_notification_number="XYZ",
            id=1,
        )
        result = PrismeResponseRestClient.map(response)
        self.assertEqual(result["afgiftsanmeldelse_id"], 1)
        self.assertEqual(result["delivery_date"], "2024-01-01")
        self.assertEqual(result["rec_id"], "ABC")
        self.assertEqual(result["tax_notification_number"], "XYZ")

    def test_map_with_id(self):
        response = PrismeResponse(
            afgiftsanmeldelse=42,
            delivery_date="2024-01-01",
            rec_id="123",
            tax_notification_number="ABC",
            id=1,
        )
        result = PrismeResponseRestClient.map(response)
        self.assertEqual(result["afgiftsanmeldelse_id"], 42)

    def test_list_parses_items(self):
        self.mock_rest.get.return_value = {
            "items": [{"rec_id": "r1"}, {"rec_id": "r2"}]
        }
        with patch(
            "told_common.rest_client.PrismeResponse.from_dict"
        ) as mock_from_dict:
            mock_from_dict.side_effect = lambda d: d
            result = self.client.list(afgiftsanmeldelse=1)
            self.assertEqual(len(result), 2)
            self.mock_rest.get.assert_called_with(
                "prismeresponse", {"afgiftsanmeldelse": 1}
            )

    def test_delete(self):
        self.client.delete(1)
        self.mock_rest.delete.assert_called_once()


class AfgiftstabelRestClientTests(TestCase):

    def setUp(self):
        self.mock_rest = MagicMock()
        self.client = AfgiftstabelRestClient(self.mock_rest)

    def test_compare_true_if_all_match(self):
        data = {"gyldig_fra": "2024-01-01", "gyldig_til": "2024-12-31", "kladde": False}
        existing = {
            "gyldig_fra": "2024-01-01",
            "gyldig_til": "2024-12-31",
            "kladde": False,
        }
        self.assertTrue(AfgiftstabelRestClient.compare(data, existing))

    def test_compare_false_on_diff(self):
        data = {"gyldig_fra": "2024-01-01", "gyldig_til": "2024-12-31", "kladde": False}
        existing = {
            "gyldig_fra": "2023-01-01",
            "gyldig_til": "2024-12-31",
            "kladde": False,
        }
        self.assertFalse(AfgiftstabelRestClient.compare(data, existing))

    def test_update_skips_if_compare_true(self):
        client = AfgiftstabelRestClient(self.mock_rest)
        client.compare = MagicMock(return_value=True)
        client.update(
            id=1, data={"gyldig_fra": "same"}, existing={"gyldig_fra": "same"}
        )
        self.mock_rest.patch.assert_not_called()

    def test_update_calls_patch_if_needed(self):
        client = AfgiftstabelRestClient(self.mock_rest)
        client.compare = MagicMock(return_value=False)
        client.update(id=1, data={"gyldig_fra": "new"}, existing={"gyldig_fra": "old"})
        self.mock_rest.patch.assert_called_once()

    def test_delete(self):
        client = AfgiftstabelRestClient(self.mock_rest)
        client.delete(123)
        self.mock_rest.delete.assert_called_with("afgiftstabel/123")


class VareafgiftssatsRestClientTests(TestCase):

    def setUp(self):
        self.mock_rest = MagicMock()
        self.client = VareafgiftssatsRestClient(self.mock_rest)

        self.item = {
            "id": 1,
            "afgiftstabel": 101,
            "vareart_da": "Spiritus",
            "vareart_kl": "A1",
            "afgiftsgruppenummer": 42,
            "enhed": "l",
            "afgiftssats": Decimal("25.50"),
            "overordnet": 2,
        }

    def test_get_populates_subs_if_sammensat(self):
        sats_dict = {
            "id": 1,
            "enhed": Vareafgiftssats.Enhed.SAMMENSAT,
            "overordnet": None,
        }
        self.mock_rest.get.side_effect = [sats_dict, {"items": []}]
        client = VareafgiftssatsRestClient(self.mock_rest)
        with patch(
            "told_common.rest_client.Vareafgiftssats.from_dict"
        ) as mock_from_dict:
            mock_obj = MagicMock()
            mock_obj.enhed = Vareafgiftssats.Enhed.SAMMENSAT
            mock_obj.overordnet = None
            mock_from_dict.return_value = mock_obj
            client.get(1)
            mock_obj.populate_subs.assert_called()

    def test_list(self):
        self.mock_rest.get.return_value = {"items": [self.item]}
        satser = self.client.list()

        sats = satser[0]
        self.assertEqual(sats.id, 1)


class EboksBeskedRestClientTests(TestCase):

    def setUp(self):
        self.mock_rest = MagicMock()
        self.client = EboksBeskedRestClient(self.mock_rest)

    def test_create_encodes_pdf_and_posts(self):
        data = {"pdf": b"some-bytes"}
        client = EboksBeskedRestClient(self.mock_rest)
        client.create(data)
        encoded = base64.b64encode(b"some-bytes").decode("ASCII")
        self.assertEqual(data["pdf"], encoded)
        self.mock_rest.post.assert_called_with("eboks", data)


class UserRestClientTests(TestCase):

    def setUp(self):
        self.mock_rest = MagicMock()
        self.client = UserRestClient(self.mock_rest)

    def test_list_returns_count_and_users(self):
        self.mock_rest.get.return_value = {"count": 2, "items": [{"id": 1}, {"id": 2}]}
        client = UserRestClient(self.mock_rest)
        with patch("told_common.rest_client.User.from_dict", side_effect=lambda x: x):
            count, users = client.list(role="test")
            self.assertEqual(count, 2)
            self.assertEqual(len(users), 2)
            self.mock_rest.get.assert_called_with("user", {"role": "test"})


class TotpDeviceRestClientTests(TestCase):

    def setUp(self):
        self.mock_rest = MagicMock()
        self.client = TotpDeviceRestClient(self.mock_rest)

    def test_get_for_user_calls_correct_endpoint(self):
        user = MagicMock()
        user.id = 123
        self.mock_rest.get.return_value = [{"id": 1}]
        client = TotpDeviceRestClient(self.mock_rest)
        with patch(
            "told_common.rest_client.TOTPDevice.from_dict", side_effect=lambda x: x
        ):
            result = client.get_for_user(user)
            self.assertEqual(result[0]["id"], 1)
            self.mock_rest.get.assert_called_with("totpdevice", {"user": 123})

    def test_create(self):
        self.client.create({})
        self.mock_rest.post.assert_called_once()


class PaymentRestClientTests(TestCase):

    def setUp(self):
        self.mock_rest = MagicMock()
        self.client = PaymentRestClient(self.mock_rest)

    def test_create_posts_to_payment(self):
        data = {"foo": "bar"}
        client = PaymentRestClient(self.mock_rest)
        client.create(data)
        self.mock_rest.post.assert_called_with("payment", data)

    def test_get_by_declaration_returns_enriched_payment(self):
        client = PaymentRestClient(self.mock_rest)
        self.mock_rest.get.side_effect = [
            [{"declaration": 10}],  # payment list
            {"afsender": 1, "modtager": 2},  # declaration
            {"id": "afsender"},  # afsender
            {"id": "modtager"},  # modtager
        ]
        result = client.get_by_declaration(10)
        self.assertIn("declaration", result)
        self.assertEqual(result["declaration"]["afsender"]["id"], "afsender")

    def test_get_by_declaration_raises_when_not_found(self):
        self.mock_rest.get.return_value = []
        client = PaymentRestClient(self.mock_rest)
        with self.assertRaises(ObjectDoesNotExist):
            client.get_by_declaration(99)

    def test_refresh_posts_to_refresh_endpoint(self):
        client = PaymentRestClient(self.mock_rest)
        client.refresh(42)
        self.mock_rest.post.assert_called_with("payment/refresh/42", {})

    def test_get(self):
        self.client.get(1)
        self.mock_rest.get.assert_called_once_with("payment/1")


class RestClientTests(TestCase):
    def setUp(self):
        self.token = JwtTokenInfo(
            access_token="fake-access",
            refresh_token="fake-refresh",
            access_token_timestamp=time.time(),
        )
        self.client = RestClient(self.token)

    @patch("requests.post")
    def test_login_success(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200, json=lambda: {"access": "abc", "refresh": "xyz"}
        )

        token = RestClient.login("user", "pass")
        self.assertEqual(token.access_token, "abc")
        self.assertEqual(token.refresh_token, "xyz")

    @patch("requests.post")
    def test_check_twofactor_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        RestClient.check_twofactor(user_id=1, twofactor_token="token")
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_refresh_login(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200, json=lambda: {"access": "new-token"}
        )

        original_timestamp = self.token.access_token_timestamp
        self.client.refresh_login()

        self.assertEqual(self.client.token.access_token, "new-token")
        self.assertNotEqual(
            self.client.token.access_token_timestamp, original_timestamp
        )
        self.assertIn("Authorization", self.client.session.headers)

    @patch.object(RestClient, "get")
    def test_get_all_items_single_page(self, mock_get):
        mock_get.return_value = {"items": [{"id": 1, "foo": "bar"}]}
        result = self.client.get_all_items("some/endpoint")
        self.assertIn(1, result)
        self.assertEqual(result[1]["foo"], "bar")

    @patch.object(RestClient, "get")
    def test_get_all_items_multiple_pages(self, mock_get):
        mock_get.side_effect = [
            {"items": [{"id": i} for i in range(100)]},
            {"items": [{"id": 101}]},
        ]
        items = self.client.get_all_items("some/endpoint")
        self.assertEqual(len(items), 101)

    @patch("requests.sessions.Session.get")
    def test_get_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"foo": "bar"}
        mock_get.return_value = mock_response

        result = self.client.get("some/path")
        self.assertEqual(result["foo"], "bar")

    @patch("requests.sessions.Session.post")
    def test_post_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response

        result = self.client.post("some/path", {"x": 1})
        self.assertEqual(result["ok"], True)

    @patch("requests.sessions.Session.post")
    def test_post_failure(self, mock_post):
        response = Response()
        response.status_code = 418
        response._content = b"I'm a teapot"
        response.url = "http://testserver/api/whatever"
        mock_post.side_effect = HTTPError(response=response)

        with self.assertRaises(RestClientException):
            self.client.post("some/path", {"x": 1})

    @patch("requests.sessions.Session.patch")
    def test_patch_success(self, mock_patch):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"patched": True}
        mock_patch.return_value = mock_response

        result = self.client.patch("some/path", {"y": 2})
        self.assertEqual(result["patched"], True)

    @patch("requests.sessions.Session.delete")
    def test_delete_success(self, mock_delete):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"deleted": True}
        mock_delete.return_value = mock_response

        result = self.client.delete("some/path")
        self.assertEqual(result["deleted"], True)

    @patch("requests.sessions.Session.delete")
    def test_delete_failure(self, mock_delete):
        response = Response()
        response.status_code = 418
        response._content = b"I'm a teapot"
        response.url = "http://testserver/api/whatever"
        mock_delete.side_effect = HTTPError(response=response)

        with self.assertRaises(RestClientException):
            self.client.delete("some/path")

    def test_check_access_token_age_triggers_refresh(self):
        self.client.token.access_token_timestamp = time.time() - 10000
        with patch.object(self.client, "refresh_login") as mock_refresh:
            self.client.check_access_token_age()
            mock_refresh.assert_called_once()

    def test_uploadfile_to_base64str_none(self):
        result = RestClient._uploadfile_to_base64str(None)
        self.assertIsNone(result)

    def test_varesatser_empty_if_no_table(self):
        with patch.object(self.client, "get") as mock_get:
            mock_get.return_value = {"count": 0, "items": []}
            self.assertEqual(self.client.varesatser, {})

    def test_varesatser_all_merges_all(self):
        self.client.get = MagicMock()
        self.client.get.side_effect = [
            {"items": [{"id": 42}]},  # afgiftstabel
            {"items": [{"id": 1}, {"id": 2}]},  # varesatser
        ]
        self.client.get_all_items = MagicMock(
            return_value={
                1: {"id": 1, "værdi": 100},
                2: {"id": 2, "værdi": 200},
            }
        )
        with patch(
            "told_common.rest_client.Vareafgiftssats.from_dict", side_effect=lambda x: x
        ):
            result = self.client.varesatser_all()
            self.assertEqual(len(result), 2)

    def test_varesatser_privat(self):

        self.client.varesatser_fra = MagicMock(
            return_value={
                1: {"id": 1, "værdi": 100},
                2: {"id": 2, "værdi": 200},
            }
        )

        varesatser = self.client.varesatser_privat

        self.assertIn(1, varesatser)
        self.assertIn(2, varesatser)


class RestClientUserTests(TestCase):
    def setUp(self):
        self.token = JwtTokenInfo(
            access_token="fake-access",
            refresh_token="fake-refresh",
            access_token_timestamp=time.time(),
        )
        self.client = RestClient(self.token)

        self.session_patcher = patch(
            "told_common.rest_client.requests.sessions.Session"
        )
        self.session_class_mock = self.session_patcher.start()

        self.session_mock = MagicMock()
        self.session_class_mock.return_value = self.session_mock

        self.post_response = MagicMock()
        self.post_response.json.return_value = {"access": "fooo", "refresh": "bar"}

        self.get_response = MagicMock()
        self.get_response.json.return_value = {
            "username": "jw",
            "first_name": "John",
            "last_name": "Wick",
            "email": "i_love_my_dog@gmail.com",
            "indberetter_data": {"cvr": 123},
            "api_key": "my_key",
            "access_token": "my_token",
            "refresh_token": "my_refresh_token",
        }

        self.session_mock.post.return_value = self.post_response
        self.session_mock.get.return_value = self.get_response
        self.session_mock.patch.return_value = self.get_response

    def tearDown(self):
        self.session_patcher.stop()

    def test_get_system_rest_client(self):
        client = self.client.get_system_rest_client()
        self.assertIsInstance(client, RestClient)

    def test_login_saml_user_cvr(self):
        saml_data = {
            "cvr": "1234",
            "cpr": "0101011234",
            "firstname": "John",
            "lastname": "Wick",
            "email": "i_love_my_dog@work_mail.com",
        }
        user, token = self.client.login_saml_user(saml_data)

        self.assertIsInstance(token, JwtTokenInfo)
        self.assertEqual(user["first_name"], "John")
        self.assertEqual(user["last_name"], "Wick")

    def test_login_saml_user_cpr(self):
        saml_data = {
            "cpr": "0101011234",
            "firstname": "John",
            "lastname": "Wick",
            "email": "i_love_my_dog@gmail.com",
        }
        user, token = self.client.login_saml_user(saml_data)

        self.assertIsInstance(token, JwtTokenInfo)
        self.assertEqual(user["first_name"], "John")
        self.assertEqual(user["last_name"], "Wick")

    def test_login_saml_user_error(self):
        saml_data = {
            "cpr": "0101011234",
            "firstname": "John",
            "lastname": "Wick",
            "email": "i_love_my_dog@gmail.com",
        }

        self.session_mock.get.side_effect = RestClientException(
            status_code=123, content="foo"
        )

        with self.assertRaises(RestClientException):
            self.client.login_saml_user(saml_data)

    def test_login_saml_api_key_error(self):
        saml_data = {
            "cpr": "0101011234",
            "firstname": "John",
            "lastname": "Wick",
            "email": "i_love_my_dog@gmail.com",
        }

        def get_side_effect(url, *args, **kwargs):
            if url.endswith("/apikey"):
                raise RestClientException(status_code=123, content="foo")
            return self.get_response

        self.session_mock.get.side_effect = get_side_effect

        user, token = self.client.login_saml_user(saml_data)
        self.assertNotIn("api_key", user["indberetter_data"])
