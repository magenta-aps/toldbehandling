# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from aktør.models import Afsender, Modtager
from django.core.management.base import BaseCommand
from tabulate import tabulate


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("type", type=str)

    def handle(self, *args, **kwargs):
        aktørtype = kwargs["type"]
        if aktørtype == "afsender":
            items = Afsender.objects.all()
        elif aktørtype == "modtager":
            items = Modtager.objects.all()
        else:
            print(f"Invalid type '{aktørtype}'")
            return
        items = items.order_by("navn").values_list(
            "id",
            "navn",
            "adresse",
            "postnummer",
            "eksplicit_stedkode",
            "by",
            "postbox",
            "telefon",
            "cvr",
        )
        print(
            tabulate(
                items,
                headers=[
                    "id",
                    "Navn",
                    "Adresse",
                    "Postnummer",
                    "Stedkode",
                    "By",
                    "Postbox",
                    "Telefon",
                    "CVR",
                ],
            )
        )

def set_country():
    for afsender in Afsender.objects.filter(land__isnull=True):
        print(f"{afsender.navn} {afsender.adresse} {afsender.postnummer} {afsender.by}")
        land = input("Land: ")
        if land != "":
            afsender.land = land
            afsender.save(update_fields=["land"])
