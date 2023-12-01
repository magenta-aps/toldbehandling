# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import os

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Creates system user"

    def handle(self, *args, **options):
        system, created = User.objects.update_or_create(
            defaults={
                "first_name": "System",
                "last_name": "",
                "email": "",
                "password": make_password(os.environ["SYSTEM_USER_PASSWORD"]),
                "is_active": True,
                "is_staff": True,
                "is_superuser": False,
            },
            username="system",
        )
