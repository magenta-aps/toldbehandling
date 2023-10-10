# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from aktør.models import Afsender, Modtager
from anmeldelse.models import Afgiftsanmeldelse, Varelinje
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from forsendelse.models import Fragtforsendelse, Postforsendelse
from sats.models import Afgiftstabel, Vareafgiftssats


class Command(BaseCommand):
    help = "Creates groups"

    def handle(self, *args, **options):
        # Med disse rettigheder på plads vil et forsøg på at køre en
        # REST-kommando, som man ikke har adgang til, resultere i en HTTP 403 fra API'et
        indberettere = Group.objects.update_or_create(
            name="Indberettere",
        )
        toldmedarbejdere = Group.objects.update_or_create(
            name="Toldmedarbejdere",
        )
        afstemmere_bogholdere = Group.objects.update_or_create(
            name="Afstemmere/bogholdere",
        )
        # dataansvarlige = Group.objects.update_or_create(
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

        send_til_prisme = Permission.objects.update_or_create(
            name="Kan sende afgiftsanmeldelser til Prisme",
            codename="prisme_afgiftsanmeldelse",
            content_type=afgiftsanmeldelse_model,
        )
        se_alle_afgiftsanmeldelser = Permission.objects.update_or_create(
            name="Kan se alle afgiftsanmeldelser, ikke kun egne",
            codename="view_all_anmeldelse",
            content_type=afgiftsanmeldelse_model,
        )
        se_alle_fragtforsendelser = Permission.objects.update_or_create(
            name="Kan se alle fragtforsendeler, ikke kun egne",
            codename="view_all_fragtforsendelser",
            content_type=fragtforsendelse_model,
        )
        se_alle_postforsendelser = Permission.objects.update_or_create(
            name="Kan se alle postforsendelser, ikke kun egne",
            codename="view_all_postforsendelser",
            content_type=postforsendelse_model,
        )
        # Brugere uden denne permission kan stadig lave REST-kald
        # som defineret af deres andre permissions
        admin_site_access = Permission.objects.update_or_create(
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
        toldmedarbejdere.permissions.add(se_alle_afgiftsanmeldelser)
        toldmedarbejdere.permissions.add(se_alle_fragtforsendelser)
        toldmedarbejdere.permissions.add(se_alle_postforsendelser)

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
        afstemmere_bogholdere.permissions.add(se_alle_afgiftsanmeldelser)
        afstemmere_bogholdere.permissions.add(se_alle_fragtforsendelser)
        afstemmere_bogholdere.permissions.add(se_alle_postforsendelser)
