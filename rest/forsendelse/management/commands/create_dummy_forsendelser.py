from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from forsendelse.models import Fragtforsendelse, Postforsendelse


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        fragtforsendelse1 = Fragtforsendelse.objects.create(
            forsendelsestype=Fragtforsendelse.Forsendelsestype.SKIB,
            fragtbrevsnummer="1234",
        )
        fragtforsendelse1.fragtbrev.save("fragtbrev.txt", ContentFile("testdata"))

        fragtforsendelse2 = Fragtforsendelse.objects.create(
            forsendelsestype=Fragtforsendelse.Forsendelsestype.FLY,
            fragtbrevsnummer="5678",
        )
        fragtforsendelse2.fragtbrev.save("fragtbrev.txt", ContentFile("testdata"))

        Postforsendelse.objects.create(
            forsendelsestype=Postforsendelse.Forsendelsestype.SKIB,
            postforsendelsesnummer="1234",
        )
        Postforsendelse.objects.create(
            forsendelsestype=Postforsendelse.Forsendelsestype.FLY,
            postforsendelsesnummer="5678",
        )
