from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock

from django.test import TestCase
from told_common.data import (
    Afgiftsanmeldelse,
    Varelinje,
    encode_optional_isoformat,
    unformat_decimal,
)


class TestData(TestCase):
    def test_unformat_decimal(self):
        self.assertEquals(unformat_decimal("1,0"), Decimal("1.0"))
        self.assertEquals(unformat_decimal("1.0"), Decimal("1.0"))
        self.assertEquals(unformat_decimal("1"), Decimal("1"))
        self.assertEquals(unformat_decimal("1.000,00"), Decimal("1000.00"))
        self.assertEquals(unformat_decimal(None), None)

    def test_encode_optional_isoformat(self):
        dt = datetime(2023, 5, 17, 13, 45, 30)
        self.assertEqual(encode_optional_isoformat(dt), "2023-05-17T13:45:30")
        self.assertEqual(encode_optional_isoformat(None), None)


class AfgiftsanmeldelseTest(TestCase):
    def setUp(self):
        self.now = datetime(2024, 1, 1, 12, 0, 0)
        self.today = date(2024, 1, 1)

    def test_indberetter_returns_oprettet_på_vegne_af(self):
        anmeldelse = Afgiftsanmeldelse(
            id=1,
            afsender=None,
            modtager=None,
            fragtforsendelse=None,
            postforsendelse=None,
            leverandørfaktura_nummer=None,
            leverandørfaktura=None,
            indførselstilladelse=None,
            afgift_total=Decimal("0.00"),
            betalt=False,
            status="ny",
            dato=self.now,
            beregnet_faktureringsdato=self.today,
            notater=None,
            prismeresponses=None,
            oprettet_af={"navn": "Alice"},
            oprettet_på_vegne_af={"navn": "Bob"},
        )
        self.assertEqual(anmeldelse.indberetter, {"navn": "Bob"})

    def test_indberetter_returns_oprettet_af_if_vegne_af_is_none(self):
        anmeldelse = Afgiftsanmeldelse(
            id=1,
            afsender=None,
            modtager=None,
            fragtforsendelse=None,
            postforsendelse=None,
            leverandørfaktura_nummer=None,
            leverandørfaktura=None,
            indførselstilladelse=None,
            afgift_total=Decimal("0.00"),
            betalt=False,
            status="ny",
            dato=self.now,
            beregnet_faktureringsdato=self.today,
            notater=None,
            prismeresponses=None,
            oprettet_af={"navn": "Alice"},
            oprettet_på_vegne_af=None,
        )
        self.assertEqual(anmeldelse.indberetter, {"navn": "Alice"})

    def test_afgift_sum_sums_afgiftsbeløb(self):
        v1 = Mock(spec=Varelinje, afgiftsbeløb=Decimal("100.50"))
        v2 = Mock(spec=Varelinje, afgiftsbeløb=Decimal("200.25"))
        anmeldelse = Afgiftsanmeldelse(
            id=1,
            afsender=None,
            modtager=None,
            fragtforsendelse=None,
            postforsendelse=None,
            leverandørfaktura_nummer=None,
            leverandørfaktura=None,
            indførselstilladelse=None,
            afgift_total=Decimal("0.00"),
            betalt=False,
            status="ny",
            dato=self.now,
            beregnet_faktureringsdato=self.today,
            notater=None,
            prismeresponses=None,
            varelinjer=[v1, v2],
        )
        self.assertEqual(anmeldelse.afgift_sum, Decimal("300.75"))

    def test_forbindelsesnummer_returns_value_from_fragtforsendelse(self):
        fragt_mock = Mock()
        fragt_mock.forbindelsesnr = "ABC123"
        anmeldelse = Afgiftsanmeldelse(
            id=1,
            afsender=None,
            modtager=None,
            fragtforsendelse=fragt_mock,
            postforsendelse=None,
            leverandørfaktura_nummer=None,
            leverandørfaktura=None,
            indførselstilladelse=None,
            afgift_total=Decimal("0.00"),
            betalt=False,
            status="ny",
            dato=self.now,
            beregnet_faktureringsdato=self.today,
            notater=None,
            prismeresponses=None,
        )
        self.assertEqual(anmeldelse.forbindelsesnummer, "ABC123")

    def test_afgangsdato_from_fragtforsendelse(self):
        fragt_mock = Mock()
        fragt_mock.afgangsdato = self.today
        anmeldelse = Afgiftsanmeldelse(
            id=1,
            afsender=None,
            modtager=None,
            fragtforsendelse=fragt_mock,
            postforsendelse=None,
            leverandørfaktura_nummer=None,
            leverandørfaktura=None,
            indførselstilladelse=None,
            afgift_total=Decimal("0.00"),
            betalt=False,
            status="ny",
            dato=self.now,
            beregnet_faktureringsdato=self.today,
            notater=None,
            prismeresponses=None,
        )
        self.assertEqual(anmeldelse.afgangsdato, self.today)

    def test_afgangsdato_from_postforsendelse_if_fragtforsendelse_missing(self):
        post_mock = Mock()
        post_mock.afgangsdato = self.today
        anmeldelse = Afgiftsanmeldelse(
            id=1,
            afsender=None,
            modtager=None,
            fragtforsendelse=None,
            postforsendelse=post_mock,
            leverandørfaktura_nummer=None,
            leverandørfaktura=None,
            indførselstilladelse=None,
            afgift_total=Decimal("0.00"),
            betalt=False,
            status="ny",
            dato=self.now,
            beregnet_faktureringsdato=self.today,
            notater=None,
            prismeresponses=None,
        )
        self.assertEqual(anmeldelse.afgangsdato, self.today)
