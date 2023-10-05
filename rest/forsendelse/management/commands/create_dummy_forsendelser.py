# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import random

from django.contrib.auth.models import Group, User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from forsendelse.models import Fragtforsendelse, Postforsendelse


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        indberetter_group = Group.objects.get(name="Indberettere")
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

            fragtforsendelse = Fragtforsendelse.objects.create(
                forsendelsestype=fragtforsendelsestype,
                fragtbrevsnummer=str(i),
                forbindelsesnr=random.choice(["1337", "7331"]),
                oprettet_af=users.order_by("?").first(),
            )
            fragtforsendelse.fragtbrev.save("fragtbrev.txt", ContentFile("testdata"))

            Postforsendelse.objects.create(
                forsendelsestype=postforsendelsestype,
                postforsendelsesnummer=str(i) + "001",
                afsenderbykode=random.choice(["8200", "1050"]),
                oprettet_af=users.order_by("?").first(),
            )
