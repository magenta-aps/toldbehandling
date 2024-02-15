# SPDX-FileCopyrightText: 2023, "Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from common.models import Stedkode
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Creates stedkoder"

    def handle(self, *args, **options):
        if Stedkode.objects.count() == 0:
            print("Ingen stedkoder findes i forvejen, opretter dem")
            stedkoder = (
                (1, "TOLDFUNKTIONEN AALBORG",),
                (2, "TOLDFUNKTIONEN NUUK",),
                (10, "NANORTALIK",),
                (20, "QAQORTOQ",),
                (30, "NARSAQ",),
                (50, "PAAMIUT",),
                (60, "NUUK",),
                (70, "MANIITSOQ",),
                (80, "SISIMIUT",),
                (100, "AASIAAT",),
                (105, "KAANGATSIAQ",),
                (110, "QASIGIANNGUIT",),
                (120, "ILULISSAT",),
                (140, "QEQERTARSUAQ",),
                (150, "UUMMANNAAQ",),
                (160, "UPERNAVIK",),
                (170, "AVANERSUAQ",),
                (180, "ANGMAGSSALIK",),
                (190, "ITTOQQORTOORMIIT",),
                (280, "KANGERLUSSUAQ",),
                (301, "PITUFFIK",),
                (302, "NARSARSSUAQ",),
                (303, "GRØNNEDAL",),
                (304, "KULUSUK",),
                (305, "DANEBORG",),
                (306, "DANMARKSHAVN",),
                (307, "ELLA Ø",),
                (308, "STATION NORD",),
                (309, "FÆRINGEHAVN",),
                (311, "PRINS CHRISTIANS SUND",),
                (312, "CONSTABLE PYNT",),
                (313, "ANGISOQ",),
                (314, "MESTERS VIG",),
                (315, "ZACKENBERG",),
                (500, "GRØNLANDSFLY",),
            )
            for kode, navn in stedkoder:
                Stedkode.objects.update_or_create(
                    kode=kode, defaults={"navn": navn}
                )
