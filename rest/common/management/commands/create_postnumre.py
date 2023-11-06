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
            postnumre = (
                (3900, "Nuuk", 20),
                (3901, "Nuussuaq", 20),
                (3910, "Kangerlussuaq", 110),
                (3911, "Sisimiut", 20),
                (3912, "Maniitsoq", 20),
                (3913, "Tasiilaq", 110),
                (3915, "Kulusuk", 110),
                (3919, "Alluitsup Paa", 20),
                (3920, "Qaqortoq", 20),
                (3921, "Narsaq", 20),
                (3922, "Nanortalik", 20),
                (3923, "Narsarsuaq", 20),
                (3924, "Ikerasassuaq", 20),
                (3930, "Kangilinnguit", 20),
                (3932, "Arsuk", 20),
                (3940, "Paamiut", 20),
                (3950, "Aasiaat", 75),
                (3951, "Qasigiannguit", 75),
                (3952, "Ilulissat", 75),
                (3953, "Qeqertarsuaq", 75),
                (3955, "Kangaatsiaq", 75),
                (3961, "Uummannaq", 105),
                (3962, "Upernavik", 105),
                (3964, "Qaarsut", 105),
                (3970, "Pituffik/Dundas", 165),
                (3971, "Qaanaaq (Thule)", 165),
                (3980, "Ittoqqortoormiit", 165),
                (3985, "Constable Pynt", 165),
                (3972, "Station Nord", 0),
                (3982, "Mestersvig", 0),
                (3984, "Danmarkshavn", 0),
                (3992, "Slædepatruljen SIRIUS", 0),
            )
            for postnummer, navn, dage in postnumre:
                Postnummer.objects.update_or_create(
                    postnummer=postnummer, defaults={"navn": navn, "dage": dage}
                )
