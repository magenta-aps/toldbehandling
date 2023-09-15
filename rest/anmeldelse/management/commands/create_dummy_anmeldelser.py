import random
from datetime import date, timedelta
from decimal import Decimal

from aktør.models import Afsender, Modtager
from anmeldelse.models import Afgiftsanmeldelse
from anmeldelse.models import Varelinje
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from forsendelse.models import Fragtforsendelse, Postforsendelse
from sats.models import Vareafgiftssats


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        anmeldelse = Afgiftsanmeldelse.objects.create(
            afsender=Afsender.objects.order_by("?").first(),
            modtager=Modtager.objects.order_by("?").first(),
            fragtforsendelse=Fragtforsendelse.objects.order_by("?").first(),
            postforsendelse=None,
            leverandørfaktura_nummer="1234",
            modtager_betaler=False,
            indførselstilladelse="5678",
            betalt=False,
        )
        anmeldelse.leverandørfaktura.save(
            "leverandørfaktura.txt", ContentFile("testdata")
        )
        Varelinje.objects.create(
            afgiftsanmeldelse=anmeldelse,
            vareafgiftssats=Vareafgiftssats.objects.filter(
                overordnet__isnull=True
            ).order_by("?")[0],
            mængde=20,
            antal=100,
            fakturabeløb=Decimal("2000"),
        )
        Varelinje.objects.create(
            afgiftsanmeldelse=anmeldelse,
            vareafgiftssats=Vareafgiftssats.objects.get(afgiftsgruppenummer=72),
            mængde=None,
            antal=1,
            fakturabeløb=Decimal("400000"),
        )

        for i in range(1, 100):
            forsendelse = Postforsendelse.objects.create(
                forsendelsestype=random.choice(
                    [
                        Postforsendelse.Forsendelsestype.SKIB,
                        Postforsendelse.Forsendelsestype.FLY,
                    ]
                ),
                postforsendelsesnummer="1234",
            )

            anmeldelse = Afgiftsanmeldelse.objects.create(
                afsender=Afsender.objects.order_by("?").first(),
                modtager=Modtager.objects.order_by("?").first(),
                fragtforsendelse=None,
                postforsendelse=forsendelse,
                leverandørfaktura_nummer="5678",
                modtager_betaler=False,
                indførselstilladelse="1234",
                betalt=random.choice([False, True]),
                godkendt=random.choice([None, False, True]),
            )
            anmeldelse.dato = date.today() - timedelta(days=random.randint(0, 1000))
            anmeldelse.save(update_fields=["dato"])
            anmeldelse.leverandørfaktura.save(
                "leverandørfaktura.txt", ContentFile("testdata")
            )
            Varelinje.objects.create(
                afgiftsanmeldelse=anmeldelse,
                vareafgiftssats=Vareafgiftssats.objects.filter(
                    overordnet__isnull=True
                ).order_by("?")[0],
                mængde=random.randint(1, 400),
                antal=random.randint(1, 400),
                fakturabeløb=Decimal(random.randint(400, 40000)),
            )
