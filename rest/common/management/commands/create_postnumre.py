# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from common.models import Postnummer
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Creates postnumre"

    def handle(self, *args, **options):
        if Postnummer.objects.count() == 0:
            print("Ingen postnumre findes i forvejen, opretter dem")
            postnumre = ((3900, "Nuuk", 20),)
            for postnummer, navn, dage in postnumre:
                Postnummer.objects.create(postnummer=postnummer, navn=navn, dage=dage)
