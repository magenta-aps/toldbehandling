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
            afgiftssats=Vareafgiftssats.objects.order_by("?")[0],
            kvantum=100,
            fakturabeløb=Decimal("2000"),
        )

        anmeldelse = Afgiftsanmeldelse.objects.create(
            afsender=Afsender.objects.order_by("?").first(),
            modtager=Modtager.objects.order_by("?").first(),
            fragtforsendelse=None,
            postforsendelse=Postforsendelse.objects.order_by("?").first(),
            leverandørfaktura_nummer="5678",
            modtager_betaler=False,
            indførselstilladelse="1234",
            betalt=True,
            godkendt=True,
        )
        anmeldelse.leverandørfaktura.save(
            "leverandørfaktura.txt", ContentFile("testdata")
        )
        Varelinje.objects.create(
            afgiftsanmeldelse=anmeldelse,
            afgiftssats=Vareafgiftssats.objects.order_by("?")[0],
            kvantum=200,
            fakturabeløb=Decimal("4000"),
        )
