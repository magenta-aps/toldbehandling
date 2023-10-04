# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from django.core.management.base import BaseCommand

from aktør.models import Afsender, Modtager
import random
import string

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
                Modtager.objects.create(
                    navn=company_name,
                    adresse=random_char(5) + "vej " + str(random.randint(0, 20)),
                    postnummer=random.randint(1000, 9999),
                    by=random_char(5) + "by",
                    postbox=None,
                    telefon=str(random.randint(100000, 999999)),
                    cvr=str(random.randint(10000000, 99999999)),
                )
