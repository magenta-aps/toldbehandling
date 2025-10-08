# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import random
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from aktør.models import Afsender, Modtager, Speditør
from anmeldelse.models import (
    Afgiftsanmeldelse,
    PrismeResponse,
    PrivatAfgiftsanmeldelse,
    Varelinje,
)
from django.contrib.auth.models import Group, User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db.models import Q
from forsendelse.models import Fragtforsendelse, Postforsendelse
from sats.models import Afgiftstabel, Vareafgiftssats


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        if Afgiftsanmeldelse.objects.exists():
            # Already created data or dummy data, don't do it again
            return
        anmeldelse = Afgiftsanmeldelse.objects.create(
            afsender=Afsender.objects.order_by("?").first(),
            modtager=Modtager.objects.order_by("?").first(),
            fragtforsendelse=Fragtforsendelse.objects.first(),
            postforsendelse=None,
            leverandørfaktura_nummer="1234",
            betales_af="afsender",
            indførselstilladelse_alkohol="5678",
            indførselstilladelse_tobak="5678",
            betalt=False,
            oprettet_af=Fragtforsendelse.objects.first().oprettet_af,
        )
        anmeldelse.leverandørfaktura.save(
            "leverandørfaktura.txt", ContentFile("testdata")
        )
        today = datetime.now(tz=timezone.utc)
        tabel = Afgiftstabel.objects.filter(
            kladde=False, gyldig_fra__lt=today, gyldig_til__gt=today
        ).first()
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
                afgiftstabel=tabel, afgiftsgruppenummer=72  # personbiler
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
                betales_af="afsender",
                indførselstilladelse_alkohol="1234",
                indførselstilladelse_tobak="1234",
                betalt=random.choice([False, True]),
                status=random.choice(["ny", "afvist", "godkendt"]),
                oprettet_af=(fragtforsendelse or postforsendelse).oprettet_af,
            )
            if anmeldelse.oprettet_af.indberetter_data.cvr == 12345679:
                anmeldelse.fuldmagtshaver = Speditør.objects.get(cvr=12345678)
            dato = datetime.combine(
                (fragtforsendelse or postforsendelse).afgangsdato,
                time(12, 0, 0, tzinfo=timezone.utc),
            )

            earliest_tabel = (
                Afgiftstabel.objects.filter(kladde=False)
                .order_by("gyldig_fra")
                .first()
                .gyldig_fra
            )
            if dato < earliest_tabel:
                dato = earliest_tabel
            anmeldelse.leverandørfaktura.save(
                "leverandørfaktura.txt", ContentFile("testdata")
            )
            tabel = Afgiftstabel.objects.filter(
                Q(gyldig_til__gte=dato) | Q(gyldig_til__isnull=True),
                gyldig_fra__lte=dato,
                kladde=False,
            )
            Varelinje.objects.create(
                afgiftsanmeldelse=anmeldelse,
                vareafgiftssats=Vareafgiftssats.objects.filter(
                    overordnet__isnull=True,
                    afgiftstabel__in=tabel,
                ).order_by("?")[0],
                mængde=random.randint(1, 400),
                antal=random.randint(1, 400),
                fakturabeløb=Decimal(random.randint(400, 40000)),
            )
            if anmeldelse.status == "godkendt":
                if random.choice([False, True]):
                    PrismeResponse.objects.create(
                        afgiftsanmeldelse=anmeldelse,
                        rec_id=random.randint(1000000000, 9999999999),
                        tax_notification_number=random.randint(10000000, 99999999),
                        delivery_date=datetime.combine(
                            date.today(), datetime.min.time(), tzinfo=timezone.utc
                        ),
                    )

        indberetter_group = Group.objects.get(name="PrivatIndberettere")
        users = User.objects.filter(groups=indberetter_group)
        if users.count() == 0:
            users = User.objects.all()
        for i in range(0, 20):
            anmeldelse = PrivatAfgiftsanmeldelse.objects.create(
                cpr=random.randint(1000000000, 9999999999),
                navn=random.choice(["Jens", "Peter", "Hans", "Søren", "Niels"])
                + " "
                + random.choice(
                    ["Jensen", "Petersen", "Hansen", "Sørensen", "Nielsen"]
                ),
                adresse="Ligustervænget " + str(random.randint(1, 100)),
                postnummer=1234,
                by="TestBy",
                telefon=str(random.randint(100000, 999999)),
                bookingnummer=str(random.randint(100000, 999999)),
                leverandørfaktura_nummer=str(random.randint(100000, 999999)),
                indførselstilladelse=None,
                indleveringsdato=date.today() + timedelta(days=random.randint(10, 30)),
                status=random.choice(["ny", "afvist", "godkendt"]),
                oprettet_af=users.order_by("?").first(),
            )
            anmeldelse.leverandørfaktura.save(
                "leverandørfaktura.txt", ContentFile("testdata")
            )
            indleveringsdato = datetime.combine(
                anmeldelse.indleveringsdato, datetime.min.time(), tzinfo=timezone.utc
            )
            tabel = Afgiftstabel.objects.filter(
                Q(gyldig_til__gte=indleveringsdato) | Q(gyldig_til__isnull=True),
                gyldig_fra__lte=indleveringsdato,
            )
            for j in range(1, 5):
                Varelinje.objects.create(
                    privatafgiftsanmeldelse=anmeldelse,
                    vareafgiftssats=Vareafgiftssats.objects.filter(
                        overordnet__isnull=True,
                        afgiftstabel__in=tabel,
                    ).order_by("?")[0],
                    mængde=random.randint(1, 400),
                    antal=random.randint(1, 400),
                    fakturabeløb=Decimal(random.randint(400, 40000)),
                )
