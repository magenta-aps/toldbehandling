from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
import random

from forsendelse.models import Fragtforsendelse, Postforsendelse


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
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
            )
            fragtforsendelse.fragtbrev.save("fragtbrev.txt", ContentFile("testdata"))

            Postforsendelse.objects.create(
                forsendelsestype=postforsendelsestype,
                postforsendelsesnummer=str(i) + "001",
                afsenderbykode=random.choice(["8200", "1050"]),
            )
