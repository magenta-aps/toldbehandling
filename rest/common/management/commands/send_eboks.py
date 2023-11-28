from common.eboks import EboksClient
from common.models import EboksBesked
from django.core.management.base import BaseCommand
from requests import HTTPError


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        beskeder = EboksBesked.objects.filter(sendt=False).order_by("opdateret")
        if beskeder.exists():
            print(f"{len(beskeder)} der skal sendes")
            client = EboksClient.from_settings()
            for besked in beskeder:
                try:
                    client.send_message(besked)
                except HTTPError:
                    pass
