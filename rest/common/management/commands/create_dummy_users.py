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
