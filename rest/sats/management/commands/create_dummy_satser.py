from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from sats.models import Afgiftstabel, Vareafgiftssats


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        tabel1 = Afgiftstabel.objects.create(
            gyldig_fra=date(date.today().year, 1, 1),
            gyldig_til=date(date.today().year, 12, 31),
            kladde=False,
        )
        tabel2 = Afgiftstabel.objects.create(
            gyldig_fra=date(date.today().year + 1, 1, 1),
            gyldig_til=None,
            kladde=False,
        )
        tabel3 = Afgiftstabel.objects.create(
            gyldig_fra=None,
            gyldig_til=None,
            kladde=True,
        )
        for tabel in (tabel1, tabel2, tabel3):
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=1,
                vareart="SUKKER og sirup",
                enhed=Vareafgiftssats.Enhed.KG,
                minimumsbeløb=False,
                afgiftssats=Decimal("6.00"),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=2,
                vareart="KAFFE, pulverkaffe, koncentrater",
                enhed=Vareafgiftssats.Enhed.KG,
                minimumsbeløb=False,
                afgiftssats=Decimal("6.00"),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=3,
                vareart="THE, pulver The, koncentrater",
                enhed=Vareafgiftssats.Enhed.KG,
                minimumsbeløb=False,
                afgiftssats=Decimal("6.60"),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=4,
                vareart="CHOKOLADE, lakrids, sukkervarer",
                enhed=Vareafgiftssats.Enhed.KG,
                minimumsbeløb=False,
                afgiftssats=Decimal("58.00"),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=11,
                vareart="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) med et ethanol indhold)på 1,21 til og med 3,09 volumenprocent.på 1,21 til og med 3,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=Decimal("3.50"),
                kræver_indførselstilladelse=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=12,
                vareart="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) med et ethanol indhold)- 3,10 - 4,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=Decimal("8.00"),
                kræver_indførselstilladelse=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=13,
                vareart="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) med et ethanol indhold)- 4,10 - 5,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=Decimal("21.00"),
                kræver_indførselstilladelse=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=14,
                vareart="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) med et ethanol indhold)- 5,10 - 7,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=Decimal("30.00"),
                kræver_indførselstilladelse=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=15,
                vareart="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) med et ethanol indhold)- 7,10 - 9,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=Decimal("43.00"),
                kræver_indførselstilladelse=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=16,
                vareart="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) med et ethanol indhold)- 9,10 - 11,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=Decimal("56.00"),
                kræver_indførselstilladelse=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=17,
                vareart="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) med et ethanol indhold)- 11,10 - 13,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=Decimal("66.00"),
                kræver_indførselstilladelse=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=18,
                vareart="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) med et ethanol indhold)- 13,10 - 15,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=Decimal("92.00"),
                kræver_indførselstilladelse=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=19,
                vareart="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) med et ethanol indhold)- 15,10 - 18,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=Decimal("114.00"),
                kræver_indførselstilladelse=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=20,
                vareart="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) med et ethanol indhold)- 18,10 - 22,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=Decimal("147.00"),
                kræver_indførselstilladelse=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=21,
                vareart="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) med et ethanol indhold)- 22,10 - 26,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=Decimal("187.00"),
                kræver_indførselstilladelse=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=22,
                vareart="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) med et ethanol indhold)- 26,10 - 30,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=Decimal("230.00"),
                kræver_indførselstilladelse=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=23,
                vareart="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) med et ethanol indhold)- 30,10 - 35,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=Decimal("280.00"),
                kræver_indførselstilladelse=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=24,
                vareart="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) med et ethanol indhold)- 35,10 - 45,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=Decimal("361.00"),
                kræver_indførselstilladelse=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=25,
                vareart="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) med et ethanol indhold)- 45,10 - 60,09 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=Decimal("495.00"),
                kræver_indførselstilladelse=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=26,
                vareart="ETHANOLHOLDIGE DRIKKEVARER (Øl, vin, spiritus, cider) med et ethanol indhold)- 60,10 - 100.0 volumenprocent.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=None,
                afgiftssats=Decimal("591.00"),
                kræver_indførselstilladelse=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=31,
                vareart="MINERALVAND, sodavand og andre kulsyreholdige læskedrikke.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=None,
                afgiftssats=Decimal("7.50"),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=32,
                vareart="MINERALVAND, sodavand og andre kulsyreholdige læskedrikke. Indført til Qaanaaq, Ittoqqortoormiit og Tasiilaq af erhvervsdrivende.",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=None,
                afgiftssats=Decimal("5.75"),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=33,
                vareart="LÆSKEDRIKKONCENTRAT til brug for fremstilling af kulsyreholdige drikke",
                enhed=Vareafgiftssats.Enhed.LITER,
                minimumsbeløb=False,
                afgiftssats=Decimal("46.30"),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=34,
                vareart="EMBALLAGE til drikkevarer, koncentrater og frugtsafter, excl. emballage til mælkeprodukter samt grønlandske returflasker: Med nettoindhold til og med 0,25 liter",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=False,
                afgiftssats=Decimal("2.00"),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=35,
                vareart="EMBALLAGE til drikkevarer, koncentrater og frugtsafter, excl. emballage til mælkeprodukter samt grønlandske returflasker: Med nettoindhold på over 0,25 liter",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=False,
                afgiftssats=Decimal("3.50"),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=41,
                vareart="CIGARER, cerutter & cigarillos 3 gr. pr. stk. og derunder",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=False,
                afgiftssats=Decimal("1.30"),
                kræver_indførselstilladelse=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=42,
                vareart="CIGARER, cerutter & cigarillos over 3 gr.",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=False,
                afgiftssats=Decimal("1.58"),
                kræver_indførselstilladelse=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=43,
                vareart="CIGARETTER",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=False,
                afgiftssats=Decimal("2.23"),
                kræver_indførselstilladelse=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=44,
                vareart="CIGARETPAPIR, inkl. hylstre",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=False,
                afgiftssats=Decimal("0.48"),
                kræver_indførselstilladelse=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=45,
                vareart="TOBAK, grovskåren, granuleret, plader over 1,5 mm snitbredde",
                enhed=Vareafgiftssats.Enhed.KG,
                minimumsbeløb=False,
                afgiftssats=Decimal("492.00"),
                kræver_indførselstilladelse=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=46,
                vareart="ANDEN RØGTOBAK, finskåren under 1,5 mm snitbredde",
                enhed=Vareafgiftssats.Enhed.KG,
                minimumsbeløb=False,
                afgiftssats=Decimal("1165.00"),
                kræver_indførselstilladelse=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=47,
                vareart="SNUS / SKRÅ og andet røgfri tobak",
                enhed=Vareafgiftssats.Enhed.PROCENT,
                minimumsbeløb=False,
                afgiftssats=Decimal("300.00"),
                kræver_indførselstilladelse=True,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=51,
                vareart="LAMME & FÅREKØD og produkter heraf",
                enhed=Vareafgiftssats.Enhed.KG,
                minimumsbeløb=False,
                afgiftssats=Decimal("25.00"),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=52,
                vareart="KØD af hornkvæg og produkter heraf, fersk eller kølet",
                enhed=Vareafgiftssats.Enhed.KG,
                minimumsbeløb=False,
                afgiftssats=Decimal("10.00"),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=53,
                vareart="KØD af hornkvæg og produkter heraf, frosset",
                enhed=Vareafgiftssats.Enhed.KG,
                minimumsbeløb=False,
                afgiftssats=Decimal("6.75"),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=54,
                vareart="SVINEKØD og produkter heraf, fersk, frosset eller kølet",
                enhed=Vareafgiftssats.Enhed.KG,
                minimumsbeløb=False,
                afgiftssats=Decimal("2.25"),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=55,
                vareart="SVINEKØD og produkter heraf, saltet i saltlage, tørret eller røget",
                enhed=Vareafgiftssats.Enhed.KG,
                minimumsbeløb=False,
                afgiftssats=Decimal("3.25"),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=56,
                vareart="SLAGTET FJERKRÆ, fersk, frosset eller kølet",
                enhed=Vareafgiftssats.Enhed.KG,
                minimumsbeløb=False,
                afgiftssats=Decimal("3.50"),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=57,
                vareart="VARER AF LAMME- OG FÅREKØD tilberedt eller konserveret",
                enhed=Vareafgiftssats.Enhed.KG,
                minimumsbeløb=False,
                afgiftssats=Decimal("25.00"),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=58,
                vareart="VARER AF HORNKVÆG, tilberedt eller konserveret",
                enhed=Vareafgiftssats.Enhed.KG,
                minimumsbeløb=False,
                afgiftssats=Decimal("4.00"),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=59,
                vareart="VARER AF SVINEKØD, tilberedt eller konserveret",
                enhed=Vareafgiftssats.Enhed.KG,
                minimumsbeløb=False,
                afgiftssats=Decimal("2.00"),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=60,
                vareart="PØLSER af enhver art",
                enhed=Vareafgiftssats.Enhed.KG,
                minimumsbeløb=False,
                afgiftssats=Decimal("3.00"),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=61,
                vareart="VARER AF LEVER, tilberedt eller konserveret",
                enhed=Vareafgiftssats.Enhed.KG,
                minimumsbeløb=False,
                afgiftssats=Decimal("2.50"),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=62,
                vareart="VARER AF FJERKRÆ, tilberedt eller konserveret",
                enhed=Vareafgiftssats.Enhed.KG,
                minimumsbeløb=False,
                afgiftssats=Decimal("3.50"),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=70,
                vareart="FYRVÆRKERI",
                enhed=Vareafgiftssats.Enhed.PROCENT,
                minimumsbeløb=False,
                afgiftssats=Decimal(100),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=71,
                vareart="KNALLERTER",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=False,
                afgiftssats=Decimal("2530.0"),
                kræver_indførselstilladelse=False,
            )

            personbiler = Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=72,
                vareart="PERSONBILER Afgiften svares med et fast beløb på 50.000 + 100 % af den del af fakturaværdien der overstiger 50.000 men ikke 150.000 + 125 % af resten.",
                enhed=Vareafgiftssats.Enhed.SAMMENSAT,
                minimumsbeløb=None,
                afgiftssats=Decimal(0),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                overordnet=personbiler,
                afgiftstabel=tabel,
                afgiftsgruppenummer=7201,
                vareart="PERSONBILER, fast beløb på 50.000",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=None,
                afgiftssats=Decimal(50_000),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                overordnet=personbiler,
                afgiftstabel=tabel,
                afgiftsgruppenummer=7202,
                vareart="PERSONBILER, 100% af den del af fakturaværdien der overstiger 50.000 men ikke 150.000",
                enhed=Vareafgiftssats.Enhed.PROCENT,
                segment_nedre=Decimal(50_000),
                segment_øvre=Decimal(150_000),
                minimumsbeløb=None,
                afgiftssats=Decimal(100),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                overordnet=personbiler,
                afgiftstabel=tabel,
                afgiftsgruppenummer=7202,
                vareart="PERSONBILER, 125% af fakturaværdien der overstiger 150.000",
                enhed=Vareafgiftssats.Enhed.PROCENT,
                segment_nedre=Decimal(150_000),
                minimumsbeløb=None,
                afgiftssats=Decimal(150),
                kræver_indførselstilladelse=False,
            )

            varebiler = Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=73,
                vareart="VAREBILER u/ 4 tons totalvægt. Afgiften svares med et fast beløb på 50.000 + 50 % af den del af fakturaværdien der overstiger 50.000.",
                enhed=Vareafgiftssats.Enhed.SAMMENSAT,
                minimumsbeløb=None,
                afgiftssats=Decimal(0),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                overordnet=varebiler,
                afgiftstabel=tabel,
                afgiftsgruppenummer=7301,
                vareart="VAREBILER u/ 4 tons totalvægt, fast beløb på 50.000",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=None,
                afgiftssats=Decimal(50_000),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                overordnet=varebiler,
                afgiftstabel=tabel,
                afgiftsgruppenummer=7302,
                vareart="VAREBILER u/ 4 tons totalvægt, 50 % af den del af fakturaværdien der overstiger 50.000",
                enhed=Vareafgiftssats.Enhed.PROCENT,
                segment_nedre=Decimal(50_000),
                minimumsbeløb=None,
                afgiftssats=Decimal(50),
                kræver_indførselstilladelse=False,
            )

            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=80,
                vareart="LASTBILER, BUSSER OG VAREBILER o/ 4 tons totalvægt.",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=None,
                afgiftssats=Decimal("50000.00"),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=83,
                vareart="SNESCOOTER",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=None,
                afgiftssats=Decimal("22000.00"),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=84,
                vareart="VANDSCOOTER",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=None,
                afgiftssats=Decimal("30000.00"),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=90,
                vareart="PARFUMER, kosmetik og toiletmidler undtagen: sæbe, tandplejemidler, shampoo, deodorant, badesalt, pudder & babyplejemidler",
                enhed=Vareafgiftssats.Enhed.PROCENT,
                minimumsbeløb=None,
                afgiftssats=Decimal(38),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=91,
                vareart="SPILLEAUTOMATER, elektriske billarder, målskydningsapparater m.v.",
                enhed=Vareafgiftssats.Enhed.PROCENT,
                minimumsbeløb=None,
                afgiftssats=Decimal(50),
                kræver_indførselstilladelse=False,
            )
            Vareafgiftssats.objects.create(
                afgiftstabel=tabel,
                afgiftsgruppenummer=92,
                vareart="MINDRE TERRÆNGÅENDE MOTORKØRE-TØJER",
                enhed=Vareafgiftssats.Enhed.ANTAL,
                minimumsbeløb=None,
                afgiftssats=Decimal("5000.0"),
                kræver_indførselstilladelse=False,
            )
