# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from decimal import Decimal

from anmeldelse.models import (
    Afgiftsanmeldelse,
    PrismeResponse,
    PrivatAfgiftsanmeldelse,
    Varelinje,
)
from django.core.management.base import BaseCommand
from django.db.models import Q
from told_common.data import Forsendelsestype

from rest.aktør.models import Afsender
from rest.sats.models import Vareafgiftssats


class Command(BaseCommand):

    def has(self, needle, haystacks):
        for x in haystacks:
            if needle in x:
                return True
        return False

    def handle(self, *args, **kwargs):
        output = []
        qs = (Afgiftsanmeldelse.objects.filter(
            status__in=("godkendt", "afsluttet"),
            tf3=False,
        ).exclude(afsender__cvr="17516345")
        .prefetch_related("varelinje_set"))
        list(qs)
        for anmeldelse in qs:
            padded_id = str(anmeldelse.id).zfill(5)
            date = anmeldelse.afgangsdato.strftime('%y%m%d')
            if anmeldelse.postforsendelse:
                transporttype = 50
            else:
                forsendelsestype = anmeldelse.fragtforsendelse.forsendelsestype
                if forsendelsestype == Forsendelsestype.FLY:
                    transporttype = 40  # FLY
                else:
                    transporttype = 10  # SKIB
            output.append(f"{padded_id}{date}   1{afsenderland}{transporttype}H")
            for i, linje in enumerate(anmeldelse.varelinje_set.all()):
                linje_id = str(linje.id).zfill(2)
                tarifnr = str(linje.vareafgiftssats.afgiftsgruppenummer).zfill(9)
                beløb = str(int(linje.afgiftsbeløb)).zfill(10)

                if linje.vareafgiftssats.enhed in (
                        Vareafgiftssats.Enhed.LITER,
                        Vareafgiftssats.Enhed.KILOGRAM,
                ):
                    hovedmængde = str(int(linje.mængde)).zfill(10)
                    supplerende_mængde = str(linje.antal).zfill(10)
                else:
                    hovedmængde = str(linje.antal).zfill(10)
                    supplerende_mængde = str(int(linje.mængde)).zfill(10)
                output.append(f"{padded_id}{date}{linje_id}{afsenderland}{tarifnr}{beløb}{hovedmængde}{supplerende_mængde}V")
