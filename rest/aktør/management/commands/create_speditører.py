# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from aktør.models import Speditør
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        speditører = {
            16545538: "Royal Arctic Line",
            40516611: "Blue Water Shipping",
            41955619: "Leman",
            27048226: "NTG",
            16474606: "DHL",
            25827198: "Eimskip",
            17516345: "Tusass",
        }
        for cvr, navn in speditører.items():
            Speditør.objects.update_or_create(
                cvr=cvr,
                defaults={
                    "navn": navn,
                },
            )
