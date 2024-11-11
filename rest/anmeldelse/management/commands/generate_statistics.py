# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from anmeldelse.models import (
    Afgiftsanmeldelse,
)
from django.core.management.base import BaseCommand
from django.db.models import Q
from sats.models import Vareafgiftssats
from datetime import date

class Command(BaseCommand):

    def has(self, needle, haystacks):
        for x in haystacks:
            if needle in x:
                return True
        return False

    country_codes = {
        "frankrig": 1,
        "holland": 3,
        "luxembourg": 3,
        "tyskland": 4,
        "italien": 5,
        "uk": 6,
        "irland": 7,
        "dk": 8,
        "grækenland": 9,
        "portugal": 10,
        "spanien": 11,
        "belgien": 17,
        "island": 24,
        "norge": 28,
        "sverige": 30,
        "finland": 32,
        "østrig": 38,
        "schweiz": 39,
        "færøerne": 41,
        "tyrkiet": 52,
        "estland": 53,
        "litauen": 55,
        "polen": 60,
        "tjekkiet": 61,
        "ungarn": 64,
        "bulgarien": 68,
        "rusland": 75,
        "slovenien": 91,
        "kroatien": 92,
        "marokko": 204,
        "tunesien": 212,
        "sydafrika": 388,
        "usa": 400,
        "canada": 404,
        "gl": 406,
        "mexico": 412,
        "costa rica": 436,
        "panama": 442,
        "colombia": 480,
        "brasilien": 508,
        "chile": 512,
        "cypern": 600,
        "israel": 624,
        "pakistan": 662,
        "indien": 664,
        "bangladesh": 666,
        "thailand": 680,
        "vietnam": 690,
        "indonesien": 700,
        "malaysia": 701,
        "singapore": 706,
        "filippinerne": 708,
        "kina": 720,
        "sydkorea": 728,
        "japan": 732,
        "taiwan": 736,
        "hong kong": 740,
        "australia": 800,
        "australien": 800,
        "new zealand": 804,
        "bunkering": 958,
    }

    def handle(self, *args, **kwargs):
        start_date = date(2024, 1, 1)
        end_date = date(2024, 8, 31)
        qs = (Afgiftsanmeldelse.objects.filter(
            status__in=("godkendt", "afsluttet"),
            tf3=False,
        ).filter(
            Q(Q(fragtforsendelse__afgangsdato__gte=start_date)|Q(postforsendelse__afgangsdato__gte=start_date)),
            Q(Q(fragtforsendelse__afgangsdato__lte=end_date)|Q(postforsendelse__afgangsdato__lte=end_date)),
        ).exclude(afsender__cvr="17516345"))
        output = []
        for anmeldelse in qs:
            padded_id = str(anmeldelse.id).zfill(5)
            date = anmeldelse.afgangsdato.strftime('%y%m%d')
            if anmeldelse.postforsendelse:
                transporttype = 50
            else:
                forsendelsestype = anmeldelse.fragtforsendelse.forsendelsestype
                if forsendelsestype == "F":
                    transporttype = 40  # FLY
                else:
                    transporttype = 10  # SKIB
            land = anmeldelse.afsender.land
            if land is not None:
                try:
                    afsenderland = str(country_codes[land]).zfill(3)
                except KeyError:
                    print(f"Did not find code for {land}")
                    raise
            else:
                afsenderland = "008"
            if land == "dk":
                land = "danmark"
            if land == "gl":
                land = "grønland"
            output.append(f"{padded_id}{date}   1{afsenderland}{transporttype}H                                       (id: {anmeldelse.id}, dato: {date}, land: {land}, transporttype: {transporttype})")
            for i, linje in enumerate(anmeldelse.varelinje_set.all(), 1):
                linje_id = str(i)
                tarifnr = str(linje.vareafgiftssats.afgiftsgruppenummer)
                beløb = str(int(linje.afgiftsbeløb))
                if linje.vareafgiftssats.enhed in (
                        Vareafgiftssats.Enhed.LITER,
                        Vareafgiftssats.Enhed.KILOGRAM,
                ):
                    hovedmængde = str(int(linje.mængde or 0))
                    supplerende_mængde = str(linje.antal or 0)
                else:
                    hovedmængde = str(linje.antal or 0)
                    supplerende_mængde = str(int(linje.mængde or 0))
                output.append(f"{padded_id}{date}{linje_id.zfill(2)}{afsenderland}{tarifnr.zfill(9)}{beløb.zfill(10)}{hovedmængde.zfill(10)}{supplerende_mængde.zfill(10)}V    (id: {anmeldelse.id}, dato: {date}, linje: {linje_id}, land: {land}, tarifnr: {tarifnr}, beløb: {beløb}, hovedmængde: {hovedmængde}, supplerende mængde: {supplerende_mængde})")
            output.append("")
        print("\n".join(output))
