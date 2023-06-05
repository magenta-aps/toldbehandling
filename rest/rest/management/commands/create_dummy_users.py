import os

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Creates dummy users"

    def handle(self, *args, **options):
        if settings.ENVIRONMENT in ("production", "staging"):
            raise Exception(f"Will not create dummy users in {settings.ENVIRONMENT}")

        admin, created = User.objects.update_or_create(
            # Admin user
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
