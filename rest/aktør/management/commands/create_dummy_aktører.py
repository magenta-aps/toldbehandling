# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import random
import string

from aktør.models import Afsender, Modtager, Speditør
from common.models import Postnummer
from django.core.management.base import BaseCommand

# Source: Wikipedia
company_names = [
    "Arctic Umiaq Line",
    "Atuagkat Bookstore",
    "Bank of Greenland",
    "Brugseni",
    "Diskoline",
    "Great Greenland Furhouse",
    "Greenland Airport Authority",
    "Greenland Brewhouse",
    "Kalaallit Nunaata Radioa",
    "KNI A/S",
    "Nukissiorfiit",
    "Nunaoil",
    "Nuuk TV",
    "Nuup Bussii",
    "Pilersuisoq",
    "Pisiffik",
    "Post Greenland",
    "Royal Arctic Line",
    "Royal Greenland",
    "Sermitsiaq",
    "TELE Greenland",
]


def random_char(y):
    # Returns a sequence of 'y' random chars
    word = "".join(random.choice(string.ascii_letters) for x in range(y))
    return word.capitalize()


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        if Afsender.objects.exists() or Modtager.objects.exists():
            # Already created dummy data, return
            return
        for company_name in company_names:
            if company_names.index(company_name) % 2 == 0:
                Afsender.objects.create(
                    navn=company_name,
                    adresse=random_char(5) + "vej " + str(random.randint(0, 20)),
                    postnummer=random.randint(1000, 9999),
                    by=random_char(5) + "by",
                    postbox=None,
                    telefon=str(random.randint(100000, 999999)),
                    cvr=str(random.randint(10000000, 99999999)),
                )
            else:
                postnummer_object = Postnummer.objects.order_by("?").first()
                if postnummer_object:
                    postnummer = postnummer_object.postnummer
                    by = postnummer_object.navn
                else:
                    postnummer = random.randint(1000, 9999)
                    by = random_char(5) + "by"

                Modtager.objects.create(
                    navn=company_name,
                    adresse=random_char(5) + "vej " + str(random.randint(0, 20)),
                    postnummer=postnummer,
                    by=by,
                    postbox=None,
                    telefon=str(random.randint(100000, 999999)),
                    cvr=str(random.randint(10000000, 99999999)),
                )

        Afsender.objects.create(
            navn="Testfirma1",
            adresse="Paradisæblevej 111",
            postnummer=1234,
            by="Andeby",
            postbox=None,
            telefon=str(random.randint(100000, 999999)),
            cvr=10000000,
        )
        Afsender.objects.create(
            navn="Testfirma1",
            adresse="Hestebremsebakken 1",
            postnummer=4321,
            by="Gåserød",
            postbox=None,
            telefon=str(random.randint(100000, 999999)),
            cvr=10000000,
        )
        Modtager.objects.create(
            navn="Testfirma2",
            adresse="Testvej 3",
            postnummer=1234,
            by="Testby",
            postbox=None,
            telefon=str(random.randint(100000, 999999)),
            cvr=20000000,
        )
        Modtager.objects.create(
            navn="Testfirma3",
            adresse="Testvej 4",
            postnummer=1234,
            by="Testby",
            postbox=None,
            telefon=str(random.randint(100000, 999999)),
            cvr=20000000,
        )
        Speditør.objects.create(cvr=12345678, navn="TestSpeditør")
