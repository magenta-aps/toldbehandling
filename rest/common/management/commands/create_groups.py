from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from aktør.models import Afsender, Modtager
from anmeldelse.models import Afgiftsanmeldelse, Varelinje
from forsendelse.models import Postforsendelse, Fragtforsendelse
from sats.models import Afgiftstabel, Vareafgiftssats


class Command(BaseCommand):
    help = "Creates groups"

    def handle(self, *args, **options):
        # Med disse rettigheder på plads vil et forsøg på at køre en
        # REST-kommando, som man ikke har adgang til, resultere i en HTTP 403 fra API'et

        indberettere = Group.objects.create(
            name="Indberettere",
        )
        toldmedarbejdere = Group.objects.create(
            name="Toldmedarbejdere",
        )
        afstemmere_bogholdere = Group.objects.create(
            name="Afstemmere/bogholdere",
        )
        # dataansvarlige = Group.objects.create(
        #     name="Dataansvarlige",
        # )

        afsender_model = ContentType.objects.get_for_model(
            Afsender, for_concrete_model=False
        )
        modtager_model = ContentType.objects.get_for_model(
            Modtager, for_concrete_model=False
        )
        afgiftsanmeldelse_model = ContentType.objects.get_for_model(
            Afgiftsanmeldelse, for_concrete_model=False
        )
        varelinje_model = ContentType.objects.get_for_model(
            Varelinje, for_concrete_model=False
        )
        postforsendelse_model = ContentType.objects.get_for_model(
            Postforsendelse, for_concrete_model=False
        )
        fragtforsendelse_model = ContentType.objects.get_for_model(
            Fragtforsendelse, for_concrete_model=False
        )
        afgiftstabel_model = ContentType.objects.get_for_model(
            Afgiftstabel, for_concrete_model=False
        )
        vareafgiftssats_model = ContentType.objects.get_for_model(
            Vareafgiftssats, for_concrete_model=False
        )

        user_model = ContentType.objects.get_for_model(User, for_concrete_model=False)

        send_til_prisme = Permission.objects.create(
            name="Kan sende afgiftsanmeldelser til Prisme",
            codename="prisme_afgiftsanmeldelse",
            content_type=afgiftsanmeldelse_model,
        )
        # Brugere uden denne permission kan stadig lave REST-kald
        # som defineret af deres andre permissions
        admin_site_access = Permission.objects.create(
            name="Kan logge ind på admin-sitet",
            codename="admin",
            content_type=user_model,
        )

        for action, model in (
            ("view", afsender_model),
            ("view", modtager_model),
            ("view", afgiftsanmeldelse_model),
            ("view", varelinje_model),
            ("view", postforsendelse_model),
            ("view", fragtforsendelse_model),
            ("view", afgiftstabel_model),
            ("view", vareafgiftssats_model),
            ("add", afsender_model),
            ("add", modtager_model),
            ("add", afgiftsanmeldelse_model),
            ("add", varelinje_model),
            ("add", postforsendelse_model),
            ("add", fragtforsendelse_model),
            # Ingen add på afgiftstabel og vareafgiftssats
            # Ingen change
            # Ingen delete
        ):
            indberettere.permissions.add(
                Permission.objects.get(
                    codename=f"{action}_{model.name}", content_type=model
                )
            )

        for action, model in (
            ("view", afsender_model),
            ("view", modtager_model),
            ("view", afgiftsanmeldelse_model),
            ("view", varelinje_model),
            ("view", postforsendelse_model),
            ("view", fragtforsendelse_model),
            ("view", afgiftstabel_model),
            ("view", vareafgiftssats_model),
            ("add", afsender_model),
            ("add", modtager_model),
            ("add", afgiftsanmeldelse_model),
            ("add", varelinje_model),
            ("add", postforsendelse_model),
            ("add", fragtforsendelse_model),
            # Ingen add på afgiftstabel og vareafgiftssats
            ("change", afgiftsanmeldelse_model),
            # Ingen change på andre modeller
            # Ingen delete
        ):
            toldmedarbejdere.permissions.add(
                Permission.objects.get(
                    codename=f"{action}_{model.name}", content_type=model
                )
            )
        toldmedarbejdere.permissions.add(send_til_prisme)
        toldmedarbejdere.permissions.add(admin_site_access)

        for action, model in (
            ("view", afsender_model),
            ("view", modtager_model),
            ("view", afgiftsanmeldelse_model),
            ("view", varelinje_model),
            ("view", postforsendelse_model),
            ("view", fragtforsendelse_model),
            ("view", afgiftstabel_model),
            ("view", vareafgiftssats_model),
            # Ingen add
            # Ingen change på andre modeller
            # Ingen delete
        ):
            afstemmere_bogholdere.permissions.add(
                Permission.objects.get(
                    codename=f"{action}_{model.name}", content_type=model
                )
            )
        afstemmere_bogholdere.permissions.add(admin_site_access)