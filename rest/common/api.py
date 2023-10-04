# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from typing import List

from django.contrib.auth.models import User

# Django-ninja har endnu ikke understøttelse for PATCH med filer i multipart/form-data
# Se https://github.com/vitalik/django-ninja/pull/397
# Derfor laver vi alle skrivninger (POST og PATCH)  med application/json
# og fildata liggende som Base64-strenge i json-værdier.
#
# Hvis det kommer på plads, og vi ønsker at bruge multipart/form-data, skal
# In-skemaerne ændres til ikke at have filfeltet med, og metoderne der
# håndterer post og patch skal modtage filen som et File(...) argument:
#
# @foo_router.post("/", auth=JWTAuth())
# def create_foo(self, payload: FooIn, filfeltnavn: ninja.File(...)):
#     item = Foo.objects.create(**payload.dict(), filfeltnavn=filfeltnavn)
#
from ninja import ModelSchema
from ninja_extra import api_controller, route, permissions
from ninja_jwt.authentication import JWTAuth


class UserOut(ModelSchema):
    groups: List[str]
    permissions: List[str]

    class Config:
        model = User
        model_fields = ["username", "first_name", "last_name", "email", "is_superuser"]

    @staticmethod
    def resolve_groups(user: User):
        return [group.name for group in user.groups.all()]

    @staticmethod
    def resolve_permissions(user: User):
        return user.get_all_permissions()


@api_controller(
    "/user",
    tags=["User"],
    permissions=[permissions.IsAuthenticated],
)
class UserAPI:
    @route.get(
        "",
        response=UserOut,
        auth=JWTAuth(),
        url_name="user_view",
    )
    def get_user(self, request):
        return request.user
