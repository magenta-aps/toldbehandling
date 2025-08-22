# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from aktør.models import Afsender, Modtager, Speditør
from anmeldelse.models import (
    Afgiftsanmeldelse,
    Notat,
    PrivatAfgiftsanmeldelse,
    Varelinje,
)
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from forsendelse.models import Fragtforsendelse, Postforsendelse
from payment.models import Item, Payment
from sats.models import Afgiftstabel, Vareafgiftssats


class Command(BaseCommand):
    help = "Creates groups"

    def handle(self, *args, **options):
        # Med disse rettigheder på plads vil et forsøg på at køre en
        # REST-kommando, som man ikke har adgang til, resultere i en HTTP 403 fra API'et
        cpr_indberettere, _ = Group.objects.update_or_create(
            name="PrivatIndberettere",
        )
        cvr_indberettere, _ = Group.objects.update_or_create(
            name="ErhvervIndberettere",
        )
        toldmedarbejdere, _ = Group.objects.update_or_create(
            name="Toldmedarbejdere",
        )
        afstemmere_bogholdere, _ = Group.objects.update_or_create(
            name="Afstemmere/bogholdere",
        )
        dataansvarlige, _ = Group.objects.update_or_create(
            name="Dataansvarlige",
        )
        admin_godkendere, _ = Group.objects.update_or_create(
            name="AdminGodkendere",
        )
        kontrollører, _ = Group.objects.update_or_create(
            name="Kontrollører",
        )
        admin_læs, _ = Group.objects.update_or_create(
            name="AdminLæs",
        )

        afsender_model = ContentType.objects.get_for_model(
            Afsender, for_concrete_model=False
        )
        modtager_model = ContentType.objects.get_for_model(
            Modtager, for_concrete_model=False
        )
        speditør_model = ContentType.objects.get_for_model(
            Speditør, for_concrete_model=False
        )
        afgiftsanmeldelse_model = ContentType.objects.get_for_model(
            Afgiftsanmeldelse, for_concrete_model=False
        )
        notat_model = ContentType.objects.get_for_model(Notat, for_concrete_model=False)
        privatafgiftsanmeldelse_model = ContentType.objects.get_for_model(
            PrivatAfgiftsanmeldelse, for_concrete_model=False
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
        payment_model = ContentType.objects.get_for_model(
            Payment, for_concrete_model=False
        )
        payment_item_model = ContentType.objects.get_for_model(
            Item, for_concrete_model=False
        )

        user_model = ContentType.objects.get_for_model(User, for_concrete_model=False)

        send_til_prisme, _ = Permission.objects.update_or_create(
            name="Kan sende afgiftsanmeldelser til Prisme",
            codename="prisme_afgiftsanmeldelse",
            content_type=afgiftsanmeldelse_model,
        )
        se_alle_afgiftsanmeldelser, _ = Permission.objects.update_or_create(
            name="Kan se alle afgiftsanmeldelser, ikke kun egne",
            codename="view_all_anmeldelse",
            content_type=afgiftsanmeldelse_model,
        )
        se_alle_godkendte_afgiftsanmeldelser, _ = Permission.objects.update_or_create(
            name="Kan se alle godkendte afgiftsanmeldelser",
            codename="view_approved_anmeldelse",
            content_type=afgiftsanmeldelse_model,
        )
        se_alle_private_afgiftsanmeldelser, _ = Permission.objects.update_or_create(
            name="Kan se alle private afgiftsanmeldelser, ikke kun egne",
            codename="view_all_privatafgiftsanmeldelse",
            content_type=privatafgiftsanmeldelse_model,
        )
        se_alle_fragtforsendelser, _ = Permission.objects.update_or_create(
            name="Kan se alle fragtforsendeler, ikke kun egne",
            codename="view_all_fragtforsendelser",
            content_type=fragtforsendelse_model,
        )
        se_alle_postforsendelser, _ = Permission.objects.update_or_create(
            name="Kan se alle postforsendelser, ikke kun egne",
            codename="view_all_postforsendelser",
            content_type=postforsendelse_model,
        )
        # Brugere uden denne permission kan stadig lave REST-kald
        # som defineret af deres andre permissions
        admin_site_access, _ = Permission.objects.update_or_create(
            name="Kan logge ind på admin-sitet",
            codename="admin",
            content_type=user_model,
        )
        godkend_afgiftsanmeldelser, _ = Permission.objects.update_or_create(
            name="Kan godkende og afvise afgiftsanmeldelser",
            codename="approve_reject_anmeldelse",
            content_type=afgiftsanmeldelse_model,
        )
        bank_transfer, _ = Permission.objects.update_or_create(
            name="Kan oprette payments som erklærer at der er foretaget bankoverførsel",
            codename="bank_payment",
            content_type=payment_model,
        )

        admin_tf10_list_view_required_permissions = (
            ("view", afsender_model),
            ("view", modtager_model),
            ("view", postforsendelse_model),
            ("view", fragtforsendelse_model),
            ("view", afgiftsanmeldelse_model),
            ("view", varelinje_model),
        )

        for action, model in (
            ("view", privatafgiftsanmeldelse_model),
            ("view", varelinje_model),
            ("view", afgiftstabel_model),
            ("view", vareafgiftssats_model),
            ("view", payment_model),
            ("view", payment_item_model),
            ("add", privatafgiftsanmeldelse_model),
            ("add", varelinje_model),
            ("add", payment_model),
            ("add", payment_item_model),
            ("change", privatafgiftsanmeldelse_model),
            ("change", varelinje_model),
            ("change", payment_model),
            ("change", payment_item_model),
            ("delete", varelinje_model),
        ):
            cpr_indberettere.permissions.add(
                Permission.objects.get(
                    codename=f"{action}_{model.model}", content_type=model
                )
            )

        for action, model in (
            ("view", afsender_model),
            ("view", modtager_model),
            ("view", speditør_model),
            ("view", afgiftsanmeldelse_model),
            ("view", varelinje_model),
            ("view", postforsendelse_model),
            ("view", fragtforsendelse_model),
            ("view", afgiftstabel_model),
            ("view", vareafgiftssats_model),
            ("view", notat_model),
            ("add", afsender_model),
            ("add", modtager_model),
            ("add", afgiftsanmeldelse_model),
            ("add", varelinje_model),
            ("add", postforsendelse_model),
            ("add", fragtforsendelse_model),
            ("add", notat_model),
            # Ingen add på afgiftstabel og vareafgiftssats
            ("change", afsender_model),
            ("change", modtager_model),
            ("change", afgiftsanmeldelse_model),
            ("change", varelinje_model),
            ("change", postforsendelse_model),
            ("change", fragtforsendelse_model),
            ("delete", varelinje_model),
            ("delete", postforsendelse_model),
            ("delete", fragtforsendelse_model),
            ("delete", afgiftsanmeldelse_model),
        ):
            cvr_indberettere.permissions.add(
                Permission.objects.get(
                    codename=f"{action}_{model.model}", content_type=model
                )
            )

        for action, model in (
            ("view", afsender_model),
            ("view", modtager_model),
            ("view", speditør_model),
            ("view", afgiftsanmeldelse_model),
            ("view", privatafgiftsanmeldelse_model),
            ("view", varelinje_model),
            ("view", postforsendelse_model),
            ("view", fragtforsendelse_model),
            ("view", afgiftstabel_model),
            ("view", vareafgiftssats_model),
            ("view", payment_model),
            ("view", payment_item_model),
            ("view", notat_model),
            ("add", afsender_model),
            ("add", modtager_model),
            ("add", afgiftsanmeldelse_model),
            ("add", varelinje_model),
            ("add", postforsendelse_model),
            ("add", fragtforsendelse_model),
            # Ingen add på afgiftstabel og vareafgiftssats
            ("add", payment_model),
            ("add", payment_item_model),
            ("add", notat_model),
            ("change", afgiftsanmeldelse_model),
            ("change", privatafgiftsanmeldelse_model),
            ("change", afsender_model),
            ("change", modtager_model),
            ("change", varelinje_model),
            ("change", postforsendelse_model),
            ("change", fragtforsendelse_model),
            ("delete", afgiftsanmeldelse_model),
            ("delete", varelinje_model),
            ("delete", postforsendelse_model),
            ("delete", fragtforsendelse_model),
            # Ingen change på andre modeller
            # Ingen delete
        ):
            toldmedarbejdere.permissions.add(
                Permission.objects.get(
                    codename=f"{action}_{model.model}", content_type=model
                )
            )
        for permission in (
            send_til_prisme,
            admin_site_access,
            se_alle_afgiftsanmeldelser,
            se_alle_fragtforsendelser,
            se_alle_postforsendelser,
            godkend_afgiftsanmeldelser,
            bank_transfer,
            se_alle_private_afgiftsanmeldelser,
        ):
            toldmedarbejdere.permissions.add(permission)

        for action, model in (
            ("view", afsender_model),
            ("view", modtager_model),
            ("view", speditør_model),
            ("view", afgiftsanmeldelse_model),
            ("view", varelinje_model),
            ("view", postforsendelse_model),
            ("view", fragtforsendelse_model),
            ("view", afgiftstabel_model),
            ("view", vareafgiftssats_model),
            ("view", payment_model),
            ("view", payment_item_model),
            ("view", notat_model),
            # Ingen add
            # Ingen change på andre modeller
            # Ingen delete
        ):
            afstemmere_bogholdere.permissions.add(
                Permission.objects.get(
                    codename=f"{action}_{model.model}", content_type=model
                )
            )
        for permission in (
            send_til_prisme,
            admin_site_access,
            se_alle_afgiftsanmeldelser,
            se_alle_fragtforsendelser,
            se_alle_postforsendelser,
            se_alle_private_afgiftsanmeldelser,
        ):
            afstemmere_bogholdere.permissions.add(permission)

        for action, model in (
            ("view", afgiftstabel_model),
            ("view", vareafgiftssats_model),
            ("view", notat_model),
            ("add", afgiftstabel_model),
            ("add", vareafgiftssats_model),
            ("change", afgiftstabel_model),
            ("change", vareafgiftssats_model),
        ) + admin_tf10_list_view_required_permissions:
            dataansvarlige.permissions.add(
                Permission.objects.get(
                    codename=f"{action}_{model.model}", content_type=model
                )
            )
        dataansvarlige.permissions.add(admin_site_access)

        # "AdminGodkendere" permissions
        admin_godkendere.permissions.add(admin_site_access)

        for action, model in (
            ("view", afgiftstabel_model),
            ("view", vareafgiftssats_model),
            ("change", afgiftstabel_model),
            ("approve", afgiftstabel_model),
        ) + admin_tf10_list_view_required_permissions:
            admin_godkendere.permissions.add(
                Permission.objects.get(
                    codename=f"{action}_{model.model}", content_type=model
                )
            )

        for permission in (
            admin_site_access,
            se_alle_afgiftsanmeldelser,
            se_alle_fragtforsendelser,
            se_alle_postforsendelser,
            se_alle_private_afgiftsanmeldelser,
        ):
            admin_læs.permissions.add(permission)

        for action, model in (
            ("view", afgiftstabel_model),
            ("view", vareafgiftssats_model),
            ("view", speditør_model),
            ("view", privatafgiftsanmeldelse_model),
            ("view", afgiftstabel_model),
            ("view", vareafgiftssats_model),
            ("view", notat_model),
        ) + admin_tf10_list_view_required_permissions:
            admin_læs.permissions.add(
                Permission.objects.get(
                    codename=f"{action}_{model.model}", content_type=model
                )
            )

        for action, model in (
            ("view", afsender_model),
            ("view", modtager_model),
            ("view", speditør_model),
            ("view", afgiftsanmeldelse_model),
            ("view", varelinje_model),
            ("view", postforsendelse_model),
            ("view", fragtforsendelse_model),
            ("view", afgiftstabel_model),
            ("view", vareafgiftssats_model),
            ("view", notat_model),
            ("view", privatafgiftsanmeldelse_model),
        ):
            kontrollører.permissions.add(
                Permission.objects.get(
                    codename=f"{action}_{model.model}", content_type=model
                )
            )
        for permission in (
            admin_site_access,
            se_alle_godkendte_afgiftsanmeldelser,
            se_alle_fragtforsendelser,
            se_alle_postforsendelser,
            se_alle_private_afgiftsanmeldelser,
        ):
            kontrollører.permissions.add(permission)
