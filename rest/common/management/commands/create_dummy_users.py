# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import os

from common.models import IndberetterProfile
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Creates dummy users"

    def handle(self, *args, **options):
        if IndberetterProfile.objects.exists():
            # Already contains data or dummy data
            return
        if settings.ENVIRONMENT in ("production",):
            print(f"Will not create dummy users in {settings.ENVIRONMENT}")
            return
        try:
            toldmedarbejder_group = Group.objects.get(name="Toldmedarbejdere")
        except Group.DoesNotExist:
            toldmedarbejder_group = None
        try:
            afstemmere_bogholdere_group = Group.objects.get(
                name="Afstemmere/bogholdere"
            )
        except Group.DoesNotExist:
            afstemmere_bogholdere_group = None
        try:
            dataansvarlige_group = Group.objects.get(name="Dataansvarlige")
        except Group.DoesNotExist:
            dataansvarlige_group = None

        try:
            erhvervindberettere_group = Group.objects.get(name="ErhvervIndberettere")
        except Group.DoesNotExist:
            erhvervindberettere_group = None
        try:
            privatindberettere_group = Group.objects.get(name="PrivatIndberettere")
        except Group.DoesNotExist:
            privatindberettere_group = None

        try:
            admin_godkendere_group = Group.objects.get(name="AdminGodkendere")
        except Group.DoesNotExist:
            admin_godkendere_group = None

        try:
            kontrollører_group = Group.objects.get(name="Kontrollører")
        except Group.DoesNotExist:
            kontrollører_group = None

        admin, created = User.objects.update_or_create(
            defaults={
                "first_name": "Admin",
                "last_name": "",
                "email": "",
                "password": make_password(os.environ.get("ADMIN_PASSWORD", "admin")),
                "is_active": True,
                "is_staff": True,
                "is_superuser": True,
            },
            username="admin",
        )

        toldmedarbejder, created = User.objects.update_or_create(
            defaults={
                "first_name": "Toldmedarbejder",
                "last_name": "",
                "email": "",
                "password": make_password(
                    os.environ.get("TOLDMEDARBEJDER_PASSWORD", "toldmedarbejder")
                ),
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
            },
            username="toldmedarbejder",
        )
        toldmedarbejder.groups.add(toldmedarbejder_group)

        afstemmer, created = User.objects.update_or_create(
            defaults={
                "first_name": "Afstemmer",
                "last_name": "",
                "email": "",
                "password": make_password(
                    os.environ.get("AFSTEMMER_PASSWORD", "afstemmer")
                ),
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
            },
            username="afstemmer",
        )
        afstemmer.groups.add(afstemmere_bogholdere_group)

        dataansvarlig, created = User.objects.update_or_create(
            defaults={
                "first_name": "Dataansvarlig",
                "last_name": "",
                "email": "",
                "password": make_password(
                    os.environ.get("DATAANSVARLIG_PASSWORD", "dataansvarlig")
                ),
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
            },
            username="dataansvarlig",
        )
        dataansvarlig.groups.add(dataansvarlige_group)

        indberetter, created = User.objects.update_or_create(
            defaults={
                "first_name": "Anders",
                "last_name": "And",
                "email": "anders@andeby.dk",
                "password": make_password("indberetter"),
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
            },
            username="indberetter",
        )
        indberetter.groups.add(erhvervindberettere_group)
        indberetter.groups.add(privatindberettere_group)

        IndberetterProfile.objects.create(
            cpr=1111111111, cvr=12345678, user=indberetter
        )

        indberetter2, created = User.objects.update_or_create(
            defaults={
                "first_name": "Mickey",
                "last_name": "Mouse",
                "email": "mickey@andeby.dk",
                "password": make_password("indberetter2"),
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
            },
            username="indberetter2",
        )
        indberetter2.groups.add(erhvervindberettere_group)
        indberetter.groups.add(privatindberettere_group)

        IndberetterProfile.objects.create(
            cpr=2222222222, cvr=12345679, user=indberetter2
        )

        indberetter3, created = User.objects.update_or_create(
            defaults={
                "first_name": "Fedtmule",
                "last_name": "",
                "email": "fedtmule@andeby.dk",
                "password": make_password("indberetter3"),
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
            },
            username="indberetter3",
        )
        indberetter3.groups.add(privatindberettere_group)

        IndberetterProfile.objects.create(cpr=3333333333, cvr=None, user=indberetter3)

        indberetter4, created = User.objects.update_or_create(
            defaults={
                "first_name": "Dummybruger",
                "last_name": "Testersen",
                "email": "test@magenta.dk",
                "password": make_password("indberetter4"),
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
            },
            username="0111111111 / 12345678",
        )
        indberetter4.groups.add(privatindberettere_group)
        indberetter4.groups.add(erhvervindberettere_group)

        IndberetterProfile.objects.create(
            cpr=111111111, cvr=12345678, user=indberetter4
        )

        admin_godkender, created = User.objects.update_or_create(
            username="admin_godkender",
            defaults={
                "first_name": "AdminGodkender",
                "last_name": "",
                "email": "",
                "password": make_password(
                    os.environ.get("ADMIN_GODKENDER_PASSWORD", "admin_godkender")
                ),
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
            },
        )
        admin_godkender.groups.add(admin_godkendere_group)

        kontrollør, created = User.objects.update_or_create(
            username="kontrollør",
            defaults={
                "first_name": "Kontrollør",
                "last_name": "",
                "email": "",
                "password": make_password(
                    os.environ.get("KONTROLLØR_PASSWORD", "kontrollør")
                ),
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
            },
        )
        kontrollør.groups.add(kontrollører_group)
