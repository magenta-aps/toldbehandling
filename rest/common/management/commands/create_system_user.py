# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import os

from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Creates system user"

    def handle(self, *args, **options):
        user_model = ContentType.objects.get_for_model(User, for_concrete_model=False)

        can_read_apikeys, _ = Permission.objects.update_or_create(
            name="Kan læse API-nøgler",
            codename="read_apikeys",
            content_type=user_model,
        )
        can_update_users = Permission.objects.get(
            codename="change_user",
            content_type=user_model,
        )
        can_view_users = Permission.objects.get(
            codename="view_user",
            content_type=user_model,
        )

        system, created = User.objects.update_or_create(
            defaults={
                "first_name": "System",
                "last_name": "",
                "email": "",
                "is_active": True,
                "is_staff": True,
                "is_superuser": False,
            },
            username="system",
        )
        system.set_password(os.environ["SYSTEM_USER_PASSWORD"])
        system.save()
        system.user_permissions.add(can_read_apikeys)
        system.user_permissions.add(can_update_users)
        system.user_permissions.add(can_view_users)
