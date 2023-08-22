from django.core.management.base import BaseCommand

from aktør.models import Afsender, Modtager


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        Afsender.objects.create(
            navn="TestFirma1",
            adresse="Testvej 42",
            postnummer=1234,
            by="Testby",
            postbox=None,
            telefon="123456",
            cvr="12345678",
        )
        Afsender.objects.create(
            navn="TestFirma2",
            adresse="Testvej 44",
            postnummer=1234,
            by="Testby",
            postbox="15",
            telefon="123456",
            cvr="12345679",
        )
        Modtager.objects.create(
            navn="TestFirma1",
            adresse="Testvej 42",
            postnummer=1234,
            by="Testby",
            postbox=None,
            telefon="123456",
            cvr="12345678",
            kreditordning=False,
            indførselstilladelse=1,
        )
        Modtager.objects.create(
            navn="TestFirma2",
            adresse="Testvej 44",
            postnummer=1234,
            by="Testby",
            postbox="15",
            telefon="123456",
            cvr="12345679",
            kreditordning=True,
            indførselstilladelse=2,
        )
