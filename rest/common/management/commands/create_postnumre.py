# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from common.models import Postnummer
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Creates postnumre"

    def handle(self, *args, **options):
        postnumre = (
            (3900, "Nuuk", 20, 60),
            (3905, "Nuussuaq", 20, 60),
            (3910, "Kangerlussuaq", 110, 280),
            (3911, "Sisimiut", 20, 80),
            (3912, "Maniitsoq", 20, 70),
            (3913, "Tasiilaq", 110, 180),
            (3915, "Kulusuk", 110, 304),
            (3919, "Alluitsup Paa", 20, 1),
            (3920, "Qaqortoq", 20, 20),
            (3921, "Narsaq", 20, 30),
            (3922, "Nanortalik", 20, 10),
            (3923, "Narsarsuaq", 20, 302),
            (3924, "Ikerasassuaq", 20, 331),
            (3930, "Kangilinnguit", 20, 303),
            (3932, "Arsuk", 20, 50),
            (3940, "Paamiut", 20, 50),
            (3950, "Aasiaat", 75, 100),
            (3951, "Qasigiannguit", 75, 110),
            (3952, "Ilulissat", 75, 120),
            (3953, "Qeqertarsuaq", 75, 140),
            (3955, "Kangaatsiaq", 75, 105),
            (3961, "Uummannaq", 105, 150),
            (3962, "Upernavik", 105, 160),
            (3964, "Qaarsut", 105, 150),
            (3970, "Pituffik/Dundas", 165, 301),
            (3971, "Qaanaaq (Thule)", 165, 170),
            (3980, "Ittoqqortoormiit", 165, 190),
            (3985, "Constable Pynt", 165, 312),
            (3972, "Station Nord", 0, 308),
            (3982, "Mestersvig", 0, 314),
            (3984, "Danmarkshavn", 0, 306),
            (3992, "Slædepatruljen SIRIUS", 0, 305),
        )
        for postnummer, navn, dage, stedkode in postnumre:
            Postnummer.objects.update_or_create(
                postnummer=postnummer,
                defaults={
                    "navn": navn,
                    "dage": dage,
                    "stedkode": stedkode,
                },
            )
