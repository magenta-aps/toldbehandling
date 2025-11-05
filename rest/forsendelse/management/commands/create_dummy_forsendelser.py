# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import random
import string
from datetime import date, timedelta

from django.contrib.auth.models import Group, User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from forsendelse.models import Fragtforsendelse, Postforsendelse


class Command(BaseCommand):
    @staticmethod
    def random_letters(count):
        return "".join([random.choice(string.ascii_letters) for x in range(count)])

    @staticmethod
    def random_digits(count):
        return "".join([random.choice(string.digits) for x in range(count)])

    def handle(self, *args, **kwargs):
        if Fragtforsendelse.objects.exists() or Postforsendelse.objects.exists():
            # Already contains dummy data
            return
        indberetter_group = Group.objects.get(name="ErhvervIndberettere")
        users = User.objects.filter(groups=indberetter_group)
        if users.count() == 0:
            users = User.objects.all()
        for i in range(200):
            fragtforsendelsestype = random.choice(
                [
                    Fragtforsendelse.Forsendelsestype.SKIB,
                    Fragtforsendelse.Forsendelsestype.FLY,
                ]
            )
            postforsendelsestype = random.choice(
                [
                    Postforsendelse.Forsendelsestype.SKIB,
                    Postforsendelse.Forsendelsestype.FLY,
                ]
            )
            if fragtforsendelsestype == Fragtforsendelse.Forsendelsestype.SKIB:
                fragtbrevsnummer = f"{self.random_letters(5)}{self.random_digits(7)}"
                forbindelsesnummer = f"{self.random_letters(3)} {self.random_digits(3)}"
            elif fragtforsendelsestype == Fragtforsendelse.Forsendelsestype.FLY:
                fragtbrevsnummer = self.random_digits(8)
                forbindelsesnummer = self.random_digits(3)
            else:
                fragtbrevsnummer = ""
                forbindelsesnummer = ""

            fragtforsendelse = Fragtforsendelse.objects.create(
                forsendelsestype=fragtforsendelsestype,
                fragtbrevsnummer=fragtbrevsnummer,
                forbindelsesnr=forbindelsesnummer,
                oprettet_af=users.order_by("?").first(),
                afgangsdato=date.today() + timedelta(days=random.randint(-600, 600)),
            )
            fragtforsendelse.fragtbrev.save(
                "fragtbrev.txt", ContentFile("testdata", name="test_file.txt")
            )

            Postforsendelse.objects.create(
                forsendelsestype=postforsendelsestype,
                postforsendelsesnummer=str(i) + "001",
                afsenderbykode=random.choice(
                    [
                        "010",
                        "011",
                        "012",
                        "013",
                        "014",
                        "015",
                        "016",
                        "017",
                        "018",
                        "019",
                        "020",
                        "021",
                        "022",
                        "023",
                        "024",
                        "025",
                        "026",
                        "027",
                        "029",
                        "030",
                        "031",
                        "032",
                        "033",
                        "035",
                        "040",
                        "041",
                        "050",
                        "051",
                        "053",
                        "056",
                        "060",
                        "061",
                        "062",
                        "063",
                        "064",
                        "065",
                        "067",
                        "069",
                        "070",
                        "071",
                        "072",
                        "073",
                        "080",
                        "081",
                        "082",
                        "083",
                        "090",
                        "092",
                        "095",
                        "096",
                        "098",
                        "100",
                        "103",
                        "104",
                        "110",
                        "111",
                        "120",
                        "121",
                        "122",
                        "123",
                        "124",
                        "140",
                        "142",
                        "143",
                        "150",
                        "151",
                        "152",
                        "153",
                        "154",
                        "155",
                        "156",
                        "157",
                        "158",
                        "160",
                        "161",
                        "162",
                        "163",
                        "164",
                        "165",
                        "166",
                        "167",
                        "168",
                        "169",
                        "170",
                        "171",
                        "172",
                        "173",
                        "174",
                        "176",
                        "177",
                        "178",
                        "180",
                        "181",
                        "182",
                        "183",
                        "184",
                        "185",
                        "186",
                        "187",
                        "188",
                        "189",
                        "190",
                        "191",
                        "192",
                        "194",
                        "195",
                        "196",
                        "200",
                        "223",
                        "224",
                        "225",
                    ]
                ),
                oprettet_af=users.order_by("?").first(),
                afgangsdato=date.today() + timedelta(days=random.randint(-600, 600)),
            )
