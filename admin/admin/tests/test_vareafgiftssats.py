# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from decimal import Decimal
from unittest.mock import MagicMock

from django.test import TestCase
from told_common.data import Vareafgiftssats, format_decimal, format_int


class VareafgiftsSatsTest(TestCase):
    def test_text(self):
        sats1 = Vareafgiftssats(
            id=1,
            afgiftstabel=1,
            afgiftsgruppenummer=1,
            vareart_da="SUKKER og sirup",
            vareart_kl="SUKKER og sirup",
            enhed=Vareafgiftssats.Enhed.KILOGRAM,
            minimumsbeløb=False,
            afgiftssats=Decimal("6.00"),
            alkohol_indførselstilladelse=False,
            tobak_indførselstilladelse=False,
            har_privat_tillægsafgift_alkohol=False,
        )
        sats1a = Vareafgiftssats(
            id=1,
            afgiftstabel=1,
            afgiftsgruppenummer=1,
            vareart_da="SUKKER og sirup",
            vareart_kl="SUKKER og sirup",
            enhed=Vareafgiftssats.Enhed.KILOGRAM,
            minimumsbeløb=False,
            afgiftssats=Decimal("6.00"),
            alkohol_indførselstilladelse=False,
            tobak_indførselstilladelse=False,
            har_privat_tillægsafgift_alkohol=False,
            segment_nedre=Decimal(200),
        )
        sats1b = Vareafgiftssats(
            id=1,
            afgiftstabel=1,
            afgiftsgruppenummer=1,
            vareart_da="SUKKER og sirup",
            vareart_kl="SUKKER og sirup",
            enhed=Vareafgiftssats.Enhed.KILOGRAM,
            minimumsbeløb=False,
            afgiftssats=Decimal("6.00"),
            alkohol_indførselstilladelse=False,
            tobak_indførselstilladelse=False,
            har_privat_tillægsafgift_alkohol=False,
            segment_øvre=Decimal(400),
        )
        sats1c = Vareafgiftssats(
            id=1,
            afgiftstabel=1,
            afgiftsgruppenummer=1,
            vareart_da="SUKKER og sirup",
            vareart_kl="SUKKER og sirup",
            enhed=Vareafgiftssats.Enhed.KILOGRAM,
            minimumsbeløb=False,
            afgiftssats=Decimal("6.00"),
            alkohol_indførselstilladelse=False,
            tobak_indførselstilladelse=False,
            har_privat_tillægsafgift_alkohol=False,
            segment_nedre=Decimal(200),
            segment_øvre=Decimal(400),
        )

        sats2 = Vareafgiftssats(
            id=1,
            afgiftstabel=1,
            afgiftsgruppenummer=1,
            vareart_da="ETHANOLHOLDIGE DRIKKEVARER",
            vareart_kl="ETHANOLHOLDIGE DRIKKEVARER",
            enhed=Vareafgiftssats.Enhed.LITER,
            minimumsbeløb=False,
            afgiftssats=Decimal("3.5"),
            alkohol_indførselstilladelse=False,
            tobak_indførselstilladelse=False,
            har_privat_tillægsafgift_alkohol=True,
        )
        sats2a = Vareafgiftssats(
            id=1,
            afgiftstabel=1,
            afgiftsgruppenummer=1,
            vareart_da="ETHANOLHOLDIGE DRIKKEVARER",
            vareart_kl="ETHANOLHOLDIGE DRIKKEVARER",
            enhed=Vareafgiftssats.Enhed.LITER,
            minimumsbeløb=False,
            afgiftssats=Decimal("3.5"),
            alkohol_indførselstilladelse=False,
            tobak_indførselstilladelse=False,
            har_privat_tillægsafgift_alkohol=True,
            segment_nedre=Decimal(200),
        )
        sats2b = Vareafgiftssats(
            id=1,
            afgiftstabel=1,
            afgiftsgruppenummer=1,
            vareart_da="ETHANOLHOLDIGE DRIKKEVARER",
            vareart_kl="ETHANOLHOLDIGE DRIKKEVARER",
            enhed=Vareafgiftssats.Enhed.LITER,
            minimumsbeløb=False,
            afgiftssats=Decimal("3.5"),
            alkohol_indførselstilladelse=False,
            tobak_indførselstilladelse=False,
            har_privat_tillægsafgift_alkohol=True,
            segment_øvre=Decimal(400),
        )
        sats2c = Vareafgiftssats(
            id=1,
            afgiftstabel=1,
            afgiftsgruppenummer=1,
            vareart_da="ETHANOLHOLDIGE DRIKKEVARER",
            vareart_kl="ETHANOLHOLDIGE DRIKKEVARER",
            enhed=Vareafgiftssats.Enhed.LITER,
            minimumsbeløb=False,
            afgiftssats=Decimal("3.5"),
            alkohol_indførselstilladelse=False,
            tobak_indførselstilladelse=False,
            har_privat_tillægsafgift_alkohol=True,
            segment_nedre=Decimal(200),
            segment_øvre=Decimal(400),
        )

        sats3 = Vareafgiftssats(
            id=1,
            afgiftstabel=1,
            afgiftsgruppenummer=1,
            vareart_da="KNALLERTER",
            vareart_kl="KNALLERTER",
            enhed=Vareafgiftssats.Enhed.ANTAL,
            minimumsbeløb=False,
            afgiftssats=Decimal(2530),
            alkohol_indførselstilladelse=False,
            tobak_indførselstilladelse=False,
            har_privat_tillægsafgift_alkohol=False,
        )
        sats3a = Vareafgiftssats(
            id=1,
            afgiftstabel=1,
            afgiftsgruppenummer=1,
            vareart_da="KNALLERTER",
            vareart_kl="KNALLERTER",
            enhed=Vareafgiftssats.Enhed.ANTAL,
            minimumsbeløb=False,
            afgiftssats=Decimal(2530),
            alkohol_indførselstilladelse=False,
            tobak_indførselstilladelse=False,
            har_privat_tillægsafgift_alkohol=False,
            segment_nedre=Decimal(200),
        )
        sats3b = Vareafgiftssats(
            id=1,
            afgiftstabel=1,
            afgiftsgruppenummer=1,
            vareart_da="KNALLERTER",
            vareart_kl="KNALLERTER",
            enhed=Vareafgiftssats.Enhed.ANTAL,
            minimumsbeløb=False,
            afgiftssats=Decimal(2530),
            alkohol_indførselstilladelse=False,
            tobak_indførselstilladelse=False,
            har_privat_tillægsafgift_alkohol=False,
            segment_øvre=Decimal(400),
        )
        sats3c = Vareafgiftssats(
            id=1,
            afgiftstabel=1,
            afgiftsgruppenummer=1,
            vareart_da="KNALLERTER",
            vareart_kl="KNALLERTER",
            enhed=Vareafgiftssats.Enhed.ANTAL,
            minimumsbeløb=False,
            afgiftssats=Decimal(2530),
            alkohol_indførselstilladelse=False,
            tobak_indførselstilladelse=False,
            har_privat_tillægsafgift_alkohol=False,
            segment_nedre=Decimal(200),
            segment_øvre=Decimal(400),
        )

        sats4 = Vareafgiftssats(
            id=1,
            afgiftstabel=1,
            afgiftsgruppenummer=1,
            vareart_da="FYRVÆRKERI",
            vareart_kl="FYRVÆRKERI",
            enhed=Vareafgiftssats.Enhed.PROCENT,
            minimumsbeløb=False,
            afgiftssats=Decimal(100),
            alkohol_indførselstilladelse=False,
            tobak_indførselstilladelse=False,
            har_privat_tillægsafgift_alkohol=False,
        )
        sats4a = Vareafgiftssats(
            id=1,
            afgiftstabel=1,
            afgiftsgruppenummer=1,
            vareart_da="FYRVÆRKERI",
            vareart_kl="FYRVÆRKERI",
            enhed=Vareafgiftssats.Enhed.PROCENT,
            minimumsbeløb=False,
            afgiftssats=Decimal(100),
            alkohol_indførselstilladelse=False,
            tobak_indførselstilladelse=False,
            har_privat_tillægsafgift_alkohol=False,
            segment_nedre=Decimal(200),
        )
        sats4b = Vareafgiftssats(
            id=1,
            afgiftstabel=1,
            afgiftsgruppenummer=1,
            vareart_da="FYRVÆRKERI",
            vareart_kl="FYRVÆRKERI",
            enhed=Vareafgiftssats.Enhed.PROCENT,
            minimumsbeløb=False,
            afgiftssats=Decimal(100),
            alkohol_indførselstilladelse=False,
            tobak_indførselstilladelse=False,
            har_privat_tillægsafgift_alkohol=False,
            segment_øvre=Decimal(400),
        )
        sats4c = Vareafgiftssats(
            id=1,
            afgiftstabel=1,
            afgiftsgruppenummer=1,
            vareart_da="FYRVÆRKERI",
            vareart_kl="FYRVÆRKERI",
            enhed=Vareafgiftssats.Enhed.PROCENT,
            minimumsbeløb=False,
            afgiftssats=Decimal(100),
            alkohol_indførselstilladelse=False,
            tobak_indførselstilladelse=False,
            har_privat_tillægsafgift_alkohol=False,
            segment_nedre=Decimal(200),
            segment_øvre=Decimal(400),
        )

        sats7201 = Vareafgiftssats(
            id=2,
            overordnet=72,
            afgiftstabel=1,
            afgiftsgruppenummer=7201,
            vareart_da="PERSONBILER, fast beløb på 50.000",
            vareart_kl="PERSONBILER, fast beløb på 50.000",
            enhed=Vareafgiftssats.Enhed.ANTAL,
            minimumsbeløb=None,
            afgiftssats=Decimal(50_000),
            alkohol_indførselstilladelse=False,
            tobak_indførselstilladelse=False,
            har_privat_tillægsafgift_alkohol=False,
        )
        sats7202 = Vareafgiftssats(
            id=3,
            overordnet=72,
            afgiftstabel=1,
            afgiftsgruppenummer=7202,
            vareart_da="PERSONBILER, 100% af den del af fakturaværdien der overstiger 50.000 men ikke 150.000",
            vareart_kl="PERSONBILER, 100% af den del af fakturaværdien der overstiger 50.000 men ikke 150.000",
            enhed=Vareafgiftssats.Enhed.PROCENT,
            segment_nedre=Decimal(50_000),
            segment_øvre=Decimal(150_000),
            minimumsbeløb=None,
            afgiftssats=Decimal(100),
            alkohol_indførselstilladelse=False,
            tobak_indførselstilladelse=False,
            har_privat_tillægsafgift_alkohol=False,
        )
        sats7203 = Vareafgiftssats(
            id=4,
            overordnet=72,
            afgiftstabel=1,
            afgiftsgruppenummer=7202,
            vareart_da="PERSONBILER, 125% af fakturaværdien der overstiger 150.000",
            vareart_kl="PERSONBILER, 125% af fakturaværdien der overstiger 150.000",
            enhed=Vareafgiftssats.Enhed.PROCENT,
            segment_nedre=Decimal(150_000),
            minimumsbeløb=None,
            afgiftssats=Decimal(150),
            alkohol_indførselstilladelse=False,
            tobak_indførselstilladelse=False,
            har_privat_tillægsafgift_alkohol=False,
        )
        sats72 = Vareafgiftssats(
            id=1,
            afgiftstabel=1,
            afgiftsgruppenummer=72,
            vareart_da="PERSONBILER Afgiften svares med et fast beløb på 50.000 + 100 % af den del af fakturaværdien der overstiger 50.000 men ikke 150.000 + 125 % af resten.",
            vareart_kl="PERSONBILER Afgiften svares med et fast beløb på 50.000 + 100 % af den del af fakturaværdien der overstiger 50.000 men ikke 150.000 + 125 % af resten.",
            enhed=Vareafgiftssats.Enhed.SAMMENSAT,
            minimumsbeløb=None,
            afgiftssats=Decimal(0),
            alkohol_indførselstilladelse=False,
            tobak_indførselstilladelse=False,
            har_privat_tillægsafgift_alkohol=False,
            subsatser=[sats7201, sats7202, sats7203],
        )
        sats72_2 = Vareafgiftssats(
            id=1,
            afgiftstabel=1,
            afgiftsgruppenummer=72,
            vareart_da="PERSONBILER Afgiften svares med et fast beløb på 50.000 + 100 % af den del af fakturaværdien der overstiger 50.000 men ikke 150.000 + 125 % af resten.",
            vareart_kl="PERSONBILER Afgiften svares med et fast beløb på 50.000 + 100 % af den del af fakturaværdien der overstiger 50.000 men ikke 150.000 + 125 % af resten.",
            enhed=Vareafgiftssats.Enhed.SAMMENSAT,
            minimumsbeløb=None,
            afgiftssats=Decimal(0),
            kræver_indførselstilladelse=False,
            har_privat_tillægsafgift_alkohol=False,
            subsatser=None,
        )

        self.assertEquals(sats1.text, "6,00 kr. pr kg")
        self.assertEquals(sats1a.text, "6,00 kr. pr kg over 200,00 kg")
        self.assertEquals(sats1b.text, "6,00 kr. pr kg under 400,00 kg")
        self.assertEquals(sats1c.text, "6,00 kr. pr kg mellem 200,00 kg og 400,00 kg")

        self.assertEquals(sats2.text, "3,50 kr. pr liter")
        self.assertEquals(sats2a.text, "3,50 kr. pr liter over 200,00 liter")
        self.assertEquals(sats2b.text, "3,50 kr. pr liter under 400,00 liter")
        self.assertEquals(
            sats2c.text, "3,50 kr. pr liter mellem 200,00 liter og 400,00 liter"
        )

        self.assertEquals(sats3.text, "2.530,00 kr. pr stk")
        self.assertEquals(sats3a.text, "2.530,00 kr. pr stk over 200 stk")
        self.assertEquals(sats3b.text, "2.530,00 kr. pr stk under 400 stk")
        self.assertEquals(sats3c.text, "2.530,00 kr. pr stk mellem 200 stk og 400 stk")

        self.assertEquals(sats4.text, "100,00% af fakturabeløb")
        self.assertEquals(sats4a.text, "100,00% af fakturabeløb over 200,00")
        self.assertEquals(sats4b.text, "100,00% af fakturabeløb under 400,00")
        self.assertEquals(
            sats4c.text, "100,00% af fakturabeløb mellem 200,00 og 400,00"
        )

        self.assertEquals(sats7201.text, "50.000,00 kr. pr stk")
        self.assertEquals(
            sats7202.text, "100,00% af fakturabeløb mellem 50.000,00 og 150.000,00"
        )
        self.assertEquals(sats7203.text, "150,00% af fakturabeløb over 150.000,00")
        self.assertEquals(
            sats72.text,
            "50.000,00 kr. pr stk + 100,00% af fakturabeløb mellem 50.000,00 og 150.000,00 + 150,00% af fakturabeløb over 150.000,00",
        )
        self.assertEquals(sats72_2.text, None)

    def test_format_decimal(self):
        self.assertEquals(format_decimal(Decimal("1234.56")), "1.234,56")

    def test_format_int(self):
        self.assertEquals(format_int(Decimal("1234.00")), 1234)
        self.assertEquals(format_int(Decimal("1234.99")), 1234)

    def test_populate_subs(self):

        sats72 = Vareafgiftssats(
            id=1,
            afgiftstabel=1,
            afgiftsgruppenummer=72,
            vareart_da="PERSONBILER Afgiften svares med et fast beløb på 50.000 + 100 % af den del af fakturaværdien der overstiger 50.000 men ikke 150.000 + 125 % af resten.",
            vareart_kl="PERSONBILER Afgiften svares med et fast beløb på 50.000 + 100 % af den del af fakturaværdien der overstiger 50.000 men ikke 150.000 + 125 % af resten.",
            enhed=Vareafgiftssats.Enhed.SAMMENSAT,
            minimumsbeløb=None,
            afgiftssats=Decimal(0),
            kræver_indførselstilladelse=False,
            har_privat_tillægsafgift_alkohol=False,
            subsatser=None,
        )

        sub_getter = MagicMock()

        sub_getter.return_value = ["foo", "bar"]

        sats72.populate_subs(sub_getter)

        self.assertEqual(sats72.subsatser, ["foo", "bar"])
