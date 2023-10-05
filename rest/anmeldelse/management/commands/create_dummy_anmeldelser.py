# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import random
from datetime import date, timedelta
from decimal import Decimal

from aktør.models import Afsender, Modtager
from anmeldelse.models import Afgiftsanmeldelse, Varelinje
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from forsendelse.models import Fragtforsendelse, Postforsendelse
from sats.models import Afgiftstabel, Vareafgiftssats


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        anmeldelse = Afgiftsanmeldelse.objects.create(
            afsender=Afsender.objects.order_by("?").first(),
            modtager=Modtager.objects.order_by("?").first(),
            fragtforsendelse=Fragtforsendelse.objects.first(),
            postforsendelse=None,
            leverandørfaktura_nummer="1234",
            modtager_betaler=False,
            indførselstilladelse="5678",
            betalt=False,
            oprettet_af=Fragtforsendelse.objects.first().oprettet_af,
        )
        anmeldelse.leverandørfaktura.save(
            "leverandørfaktura.txt", ContentFile("testdata")
        )
        tabel = Afgiftstabel.objects.first()
        Varelinje.objects.create(
            afgiftsanmeldelse=anmeldelse,
            vareafgiftssats=Vareafgiftssats.objects.filter(
                overordnet__isnull=True,
                afgiftstabel=tabel,
            ).order_by("?")[0],
            mængde=20,
            antal=100,
            fakturabeløb=Decimal("2000"),
        )
        Varelinje.objects.create(
            afgiftsanmeldelse=anmeldelse,
            vareafgiftssats=Vareafgiftssats.objects.get(
                afgiftstabel=tabel, afgiftsgruppenummer=72
            ),
            mængde=None,
            antal=1,
            fakturabeløb=Decimal("400000"),
        )

        fragtforsendelser = Fragtforsendelse.objects.all()
        postforsendelser = Postforsendelse.objects.all()

        for i in range(1, 100):
            fragtforsendelse = fragtforsendelser[i] if i % 2 else None
            postforsendelse = postforsendelser[i] if not i % 2 else None
            anmeldelse = Afgiftsanmeldelse.objects.create(
                afsender=Afsender.objects.order_by("?").first(),
                modtager=Modtager.objects.order_by("?").first(),
                fragtforsendelse=fragtforsendelse,
                postforsendelse=postforsendelse,
                leverandørfaktura_nummer="5678",
                modtager_betaler=False,
                indførselstilladelse="1234",
                betalt=random.choice([False, True]),
                godkendt=random.choice([None, False, True]),
                oprettet_af=(fragtforsendelse or postforsendelse).oprettet_af,
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
