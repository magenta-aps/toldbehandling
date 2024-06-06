# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from django.core.management.base import BaseCommand
from sats.models import Afgiftstabel, Vareafgiftssats


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        if Afgiftstabel.objects.exists() or Vareafgiftssats.objects.exists():
            # Don't create dummy data more than once
            return
        tz = timezone(-timedelta(seconds=2 * 3600))
        tabel0 = Afgiftstabel.objects.create(
            gyldig_fra=datetime(1970, 1, 1, 0, 0, 0, tzinfo=tz),
            gyldig_til=datetime(date.today().year, 1, 1, 0, 0, 0, tzinfo=tz),
            kladde=False,
        )
        tabel1 = Afgiftstabel.objects.create(
            gyldig_fra=datetime(date.today().year, 1, 1, 0, 0, 0, tzinfo=tz),
            gyldig_til=datetime(date.today().year + 1, 1, 1, 0, 0, 0, tzinfo=tz),
            kladde=False,
        )
        tabel2 = Afgiftstabel.objects.create(
            gyldig_fra=datetime(date.today().year + 1, 1, 10, 0, 0, tzinfo=tz),
            gyldig_til=None,
            kladde=False,
        )
        tabel3 = Afgiftstabel.objects.create(
            gyldig_fra=None,
            gyldig_til=None,
            kladde=True,
        )
        for tabel, faktor in ((tabel0, 1), (tabel1, 2), (tabel2, 3), (tabel3, 4)):
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=1,
                vareart_da="SUKKER og sirup",
                vareart_kl="SUKKER og sirup",
                enhed=Vareafgiftssats.Enhed.KILOGRAM,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("6.00"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=2,
                vareart_da="KAFFE, pulverkaffe, koncentrater",
                vareart_kl="KAFFE, pulverkaffe, koncentrater",
                enhed=Vareafgiftssats.Enhed.KILOGRAM,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("6.00"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=3,
                vareart_da="THE, pulver The, koncentrater",
                vareart_kl="THE, pulver The, koncentrater",
                enhed=Vareafgiftssats.Enhed.KILOGRAM,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("6.60"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=4,
                vareart_da="CHOKOLADE, lakrids, sukkervarer",
                vareart_kl="CHOKOLADE, lakrids, sukkervarer",
                enhed=Vareafgiftssats.Enhed.KILOGRAM,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("58.00"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=11,
                vareart_da="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)på 1,21 til og med 3,09 "
                "volumenprocent.på 1,21 til og med 3,09 volumenprocent.",
                vareart_kl="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)på 1,21 til og med 3,09 "
                "volumenprocent.på 1,21 til og med 3,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("3.50"),
                kræver_indførselstilladelse=True,
                har_privat_tillægsafgift_alkohol=True,
                synlig_privat=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=12,
                vareart_da="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 3,10 - 4,09 volumenprocent.",
                vareart_kl="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 3,10 - 4,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("8.00"),
                kræver_indførselstilladelse=True,
                har_privat_tillægsafgift_alkohol=True,
                synlig_privat=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=13,
                vareart_da="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 4,10 - 5,09 volumenprocent.",
                vareart_kl="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 4,10 - 5,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("21.00"),
                kræver_indførselstilladelse=True,
                har_privat_tillægsafgift_alkohol=True,
                synlig_privat=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=14,
                vareart_da="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 5,10 - 7,09 volumenprocent.",
                vareart_kl="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 5,10 - 7,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("30.00"),
                kræver_indførselstilladelse=True,
                har_privat_tillægsafgift_alkohol=True,
                synlig_privat=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=15,
                vareart_da="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 7,10 - 9,09 volumenprocent.",
                vareart_kl="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 7,10 - 9,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("43.00"),
                kræver_indførselstilladelse=True,
                har_privat_tillægsafgift_alkohol=True,
                synlig_privat=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=16,
                vareart_da="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 9,10 - 11,09 volumenprocent.",
                vareart_kl="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 9,10 - 11,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("56.00"),
                kræver_indførselstilladelse=True,
                har_privat_tillægsafgift_alkohol=True,
                synlig_privat=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=17,
                vareart_da="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 11,10 - 13,09 volumenprocent.",
                vareart_kl="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 11,10 - 13,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("66.00"),
                kræver_indførselstilladelse=True,
                har_privat_tillægsafgift_alkohol=True,
                synlig_privat=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=18,
                vareart_da="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 13,10 - 15,09 volumenprocent.",
                vareart_kl="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 13,10 - 15,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("92.00"),
                kræver_indførselstilladelse=True,
                har_privat_tillægsafgift_alkohol=True,
                synlig_privat=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=19,
                vareart_da="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 15,10 - 18,09 volumenprocent.",
                vareart_kl="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 15,10 - 18,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("114.00"),
                kræver_indførselstilladelse=True,
                har_privat_tillægsafgift_alkohol=True,
                synlig_privat=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=20,
                vareart_da="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 18,10 - 22,09 volumenprocent.",
                vareart_kl="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 18,10 - 22,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("147.00"),
                kræver_indførselstilladelse=True,
                har_privat_tillægsafgift_alkohol=True,
                synlig_privat=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=21,
                vareart_da="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 22,10 - 26,09 volumenprocent.",
                vareart_kl="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 22,10 - 26,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("187.00"),
                kræver_indførselstilladelse=True,
                har_privat_tillægsafgift_alkohol=True,
                synlig_privat=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=22,
                vareart_da="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 26,10 - 30,09 volumenprocent.",
                vareart_kl="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 26,10 - 30,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("230.00"),
                kræver_indførselstilladelse=True,
                har_privat_tillægsafgift_alkohol=True,
                synlig_privat=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=23,
                vareart_da="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 30,10 - 35,09 volumenprocent.",
                vareart_kl="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 30,10 - 35,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("280.00"),
                kræver_indførselstilladelse=True,
                har_privat_tillægsafgift_alkohol=True,
                synlig_privat=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=24,
                vareart_da="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 35,10 - 45,09 volumenprocent.",
                vareart_kl="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 35,10 - 45,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("361.00"),
                kræver_indførselstilladelse=True,
                har_privat_tillægsafgift_alkohol=True,
                synlig_privat=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=25,
                vareart_da="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 45,10 - 60,09 volumenprocent.",
                vareart_kl="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 45,10 - 60,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("495.00"),
                kræver_indførselstilladelse=True,
                har_privat_tillægsafgift_alkohol=True,
                synlig_privat=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=26,
                vareart_da="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 60,10 - 100.0 volumenprocent.",
                vareart_kl="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) "
                "med et ethanol indhold)- 60,10 - 100.0 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=None,
                afgiftssats=faktor * Decimal("591.00"),
                kræver_indførselstilladelse=True,
                har_privat_tillægsafgift_alkohol=True,
                synlig_privat=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=31,
                vareart_da="MINERALVAND, sodavand og andre kulsyreholdige læskedrikke.",
                vareart_kl="MINERALVAND, sodavand og andre kulsyreholdige læskedrikke.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=None,
                afgiftssats=faktor * Decimal("7.50"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
                synlig_privat=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=32,
                vareart_da="MINERALVAND, sodavand og andre kulsyreholdige læskedrikke. "
                "Indført til Qaanaaq, Ittoqqortoormiit og Tasiilaq af "
                "erhvervsdrivende.",
                vareart_kl="MINERALVAND, sodavand og andre kulsyreholdige læskedrikke. "
                "Indført til Qaanaaq, Ittoqqortoormiit og Tasiilaq af "
                "erhvervsdrivende.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=None,
                afgiftssats=faktor * Decimal("5.75"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
                synlig_privat=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=33,
                vareart_da="LÆSKEDRIKKONCENTRAT til brug for fremstilling af "
                "kulsyreholdige drikke",
                vareart_kl="LÆSKEDRIKKONCENTRAT til brug for fremstilling af "
                "kulsyreholdige drikke",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("46.30"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=34,
                vareart_da="EMBALLAGE til drikkevarer, koncentrater og frugtsafter, "
                "excl. emballage til mælkeprodukter samt grønlandske "
                "returflasker: Med nettoindhold til og med 0,25 liter",
                vareart_kl="EMBALLAGE til drikkevarer, koncentrater og frugtsafter, "
                "excl. emballage til mælkeprodukter samt grønlandske "
                "returflasker: Med nettoindhold til og med 0,25 liter",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("2.00"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
                synlig_privat=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=35,
                vareart_da="EMBALLAGE til drikkevarer, koncentrater og frugtsafter, "
                "excl. emballage til mælkeprodukter samt grønlandske "
                "returflasker: Med nettoindhold på over 0,25 liter",
                vareart_kl="EMBALLAGE til drikkevarer, koncentrater og frugtsafter, "
                "excl. emballage til mælkeprodukter samt grønlandske "
                "returflasker: Med nettoindhold på over 0,25 liter",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("3.50"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
                synlig_privat=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=41,
                vareart_da="CIGARER, cerutter & cigarillos 3 gr. pr. stk. og derunder",
                vareart_kl="CIGARER, cerutter & cigarillos 3 gr. pr. stk. og derunder",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("1.30"),
                kræver_indførselstilladelse=True,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=42,
                vareart_da="CIGARER, cerutter & cigarillos over 3 gr.",
                vareart_kl="CIGARER, cerutter & cigarillos over 3 gr.",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("1.58"),
                kræver_indførselstilladelse=True,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=43,
                vareart_da="CIGARETTER",
                vareart_kl="CIGARETTER",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("2.23"),
                kræver_indførselstilladelse=True,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=44,
                vareart_da="CIGARETPAPIR, inkl. hylstre",
                vareart_kl="CIGARETPAPIR, inkl. hylstre",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("0.48"),
                kræver_indførselstilladelse=True,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=45,
                vareart_da="TOBAK, grovskåren, granuleret, "
                "plader over 1,5 mm snitbredde",
                vareart_kl="TOBAK, grovskåren, granuleret, "
                "plader over 1,5 mm snitbredde",
                enhed=Vareafgiftssats.Enhed.KILOGRAM,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("492.00"),
                kræver_indførselstilladelse=True,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=46,
                vareart_da="ANDEN RØGTOBAK, finskåren under 1,5 mm snitbredde",
                vareart_kl="ANDEN RØGTOBAK, finskåren under 1,5 mm snitbredde",
                enhed=Vareafgiftssats.Enhed.KILOGRAM,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("1165.00"),
                kræver_indførselstilladelse=True,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=47,
                vareart_da="SNUS / SKRÅ og andet røgfri tobak",
                vareart_kl="SNUS / SKRÅ og andet røgfri tobak",
                enhed=Vareafgiftssats.Enhed.PROCENT,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("300.00"),
                kræver_indførselstilladelse=True,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=51,
                vareart_da="LAMME & FÅREKØD og produkter heraf",
                vareart_kl="LAMME & FÅREKØD og produkter heraf",
                enhed=Vareafgiftssats.Enhed.KILOGRAM,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("25.00"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=52,
                vareart_da="KØD af hornkvæg og produkter heraf, fersk eller kølet",
                vareart_kl="KØD af hornkvæg og produkter heraf, fersk eller kølet",
                enhed=Vareafgiftssats.Enhed.KILOGRAM,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("10.00"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=53,
                vareart_da="KØD af hornkvæg og produkter heraf, frosset",
                vareart_kl="KØD af hornkvæg og produkter heraf, frosset",
                enhed=Vareafgiftssats.Enhed.KILOGRAM,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("6.75"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=54,
                vareart_da="SVINEKØD og produkter heraf, fersk, frosset eller kølet",
                vareart_kl="SVINEKØD og produkter heraf, fersk, frosset eller kølet",
                enhed=Vareafgiftssats.Enhed.KILOGRAM,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("2.25"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=55,
                vareart_da="SVINEKØD og produkter heraf, saltet i saltlage, "
                "tørret eller røget",
                vareart_kl="SVINEKØD og produkter heraf, saltet i saltlage, "
                "tørret eller røget",
                enhed=Vareafgiftssats.Enhed.KILOGRAM,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("3.25"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=56,
                vareart_da="SLAGTET FJERKRÆ, fersk, frosset eller kølet",
                vareart_kl="SLAGTET FJERKRÆ, fersk, frosset eller kølet",
                enhed=Vareafgiftssats.Enhed.KILOGRAM,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("3.50"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=57,
                vareart_da="VARER AF LAMME- OG FÅREKØD tilberedt eller konserveret",
                vareart_kl="VARER AF LAMME- OG FÅREKØD tilberedt eller konserveret",
                enhed=Vareafgiftssats.Enhed.KILOGRAM,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("25.00"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=58,
                vareart_da="VARER AF HORNKVÆG, tilberedt eller konserveret",
                vareart_kl="VARER AF HORNKVÆG, tilberedt eller konserveret",
                enhed=Vareafgiftssats.Enhed.KILOGRAM,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("4.00"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=59,
                vareart_da="VARER AF SVINEKØD, tilberedt eller konserveret",
                vareart_kl="VARER AF SVINEKØD, tilberedt eller konserveret",
                enhed=Vareafgiftssats.Enhed.KILOGRAM,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("2.00"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=60,
                vareart_da="PØLSER af enhver art",
                vareart_kl="PØLSER af enhver art",
                enhed=Vareafgiftssats.Enhed.KILOGRAM,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("3.00"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=61,
                vareart_da="VARER AF LEVER, tilberedt eller konserveret",
                vareart_kl="VARER AF LEVER, tilberedt eller konserveret",
                enhed=Vareafgiftssats.Enhed.KILOGRAM,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("2.50"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=62,
                vareart_da="VARER AF FJERKRÆ, tilberedt eller konserveret",
                vareart_kl="VARER AF FJERKRÆ, tilberedt eller konserveret",
                enhed=Vareafgiftssats.Enhed.KILOGRAM,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("3.50"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=70,
                vareart_da="FYRVÆRKERI",
                vareart_kl="FYRVÆRKERI",
                enhed=Vareafgiftssats.Enhed.PROCENT,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal(100),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=71,
                vareart_da="KNALLERTER",
                vareart_kl="KNALLERTER",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=False,
                afgiftssats=faktor * Decimal("2530.0"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )

            personbiler = Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=72,
                vareart_da="PERSONBILER Afgiften svares med et fast beløb på 50.000 "
                "+ 100 % af den del af fakturaværdien der overstiger "
                "50.000 men ikke 150.000 + 125 % af resten.",
                vareart_kl="PERSONBILER Afgiften svares med et fast beløb på 50.000 "
                "+ 100 % af den del af fakturaværdien der overstiger "
                "50.000 men ikke 150.000 + 125 % af resten.",
                enhed=Vareafgiftssats.Enhed.SAMMENSAT,
                minimumsbeløb=None,
                afgiftssats=faktor * Decimal(0),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                overordnet=personbiler,
                afgiftstabel=tabel,
                afgiftsgruppenummer=7201,
                vareart_da="PERSONBILER, fast beløb på 50.000",
                vareart_kl="PERSONBILER, fast beløb på 50.000",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=None,
                afgiftssats=faktor * Decimal(50_000),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                overordnet=personbiler,
                afgiftstabel=tabel,
                afgiftsgruppenummer=7202,
                vareart_da="PERSONBILER, 100% af den del af fakturaværdien der "
                "overstiger 50.000 men ikke 150.000",
                vareart_kl="PERSONBILER, 100% af den del af fakturaværdien der "
                "overstiger 50.000 men ikke 150.000",
                enhed=Vareafgiftssats.Enhed.PROCENT,
                segment_nedre=Decimal(50_000),
                segment_øvre=Decimal(150_000),
                minimumsbeløb=None,
                afgiftssats=faktor * Decimal(100),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                overordnet=personbiler,
                afgiftstabel=tabel,
                afgiftsgruppenummer=7203,
                vareart_da="PERSONBILER, 125% af fakturaværdien der overstiger 150.000",
                vareart_kl="PERSONBILER, 125% af fakturaværdien der overstiger 150.000",
                enhed=Vareafgiftssats.Enhed.PROCENT,
                segment_nedre=Decimal(150_000),
                minimumsbeløb=None,
                afgiftssats=faktor * Decimal(150),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )

            varebiler = Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=73,
                vareart_da="VAREBILER u/ 4 tons totalvægt. Afgiften svares med et "
                "fast beløb på 50.000 + 50 % af den del af "
                "fakturaværdien der overstiger 50.000.",
                vareart_kl="VAREBILER u/ 4 tons totalvægt. Afgiften svares med et "
                "fast beløb på 50.000 + 50 % af den del af "
                "fakturaværdien der overstiger 50.000.",
                enhed=Vareafgiftssats.Enhed.SAMMENSAT,
                minimumsbeløb=None,
                afgiftssats=faktor * Decimal(0),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                overordnet=varebiler,
                afgiftstabel=tabel,
                afgiftsgruppenummer=7301,
                vareart_da="VAREBILER u/ 4 tons totalvægt, fast beløb på 50.000",
                vareart_kl="VAREBILER u/ 4 tons totalvægt, fast beløb på 50.000",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=None,
                afgiftssats=faktor * Decimal(50_000),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                overordnet=varebiler,
                afgiftstabel=tabel,
                afgiftsgruppenummer=7302,
                vareart_da="VAREBILER u/ 4 tons totalvægt, 50 % af den del af "
                "fakturaværdien der overstiger 50.000",
                vareart_kl="VAREBILER u/ 4 tons totalvægt, 50 % af den del af "
                "fakturaværdien der overstiger 50.000",
                enhed=Vareafgiftssats.Enhed.PROCENT,
                segment_nedre=Decimal(50_000),
                minimumsbeløb=None,
                afgiftssats=faktor * Decimal(50),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )

            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=80,
                vareart_da="LASTBILER, BUSSER OG VAREBILER o/ 4 tons totalvægt.",
                vareart_kl="LASTBILER, BUSSER OG VAREBILER o/ 4 tons totalvægt.",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=None,
                afgiftssats=faktor * Decimal("50000.00"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=83,
                vareart_da="SNESCOOTER",
                vareart_kl="SNESCOOTER",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=None,
                afgiftssats=faktor * Decimal("22000.00"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=84,
                vareart_da="VANDSCOOTER",
                vareart_kl="VANDSCOOTER",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=None,
                afgiftssats=faktor * Decimal("30000.00"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=90,
                vareart_da="PARFUMER, kosmetik og toiletmidler undtagen: sæbe, "
                "tandplejemidler, shampoo, deodorant, badesalt, "
                "pudder & babyplejemidler",
                vareart_kl="PARFUMER, kosmetik og toiletmidler undtagen: sæbe, "
                "tandplejemidler, shampoo, deodorant, badesalt, "
                "pudder & babyplejemidler",
                enhed=Vareafgiftssats.Enhed.PROCENT,
                minimumsbeløb=None,
                afgiftssats=faktor * Decimal(38),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=91,
                vareart_da="SPILLEAUTOMATER, elektriske billarder, "
                "målskydningsapparater m.v.",
                vareart_kl="SPILLEAUTOMATER, elektriske billarder, "
                "målskydningsapparater m.v.",
                enhed=Vareafgiftssats.Enhed.PROCENT,
                minimumsbeløb=None,
                afgiftssats=faktor * Decimal(50),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=92,
                vareart_da="MINDRE TERRÆNGÅENDE MOTORKØRETØJER",
                vareart_kl="MINDRE TERRÆNGÅENDE MOTORKØRETØJER",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=None,
                afgiftssats=faktor * Decimal("5000.0"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=101,
                vareart_da="PANTBELAGT EMBALLAGE - PANT",
                vareart_kl="PANTBELAGT EMBALLAGE - PANT",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=False,
                afgiftssats=Decimal("2.0"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
                synlig_privat=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=102,
                vareart_da="PANTBELAGT EMBALLAGE - GEBYR",
                vareart_kl="PANTBELAGT EMBALLAGE - GEBYR",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=False,
                afgiftssats=Decimal("0.6"),
                kræver_indførselstilladelse=False,
                har_privat_tillægsafgift_alkohol=False,
                synlig_privat=True,
            )
