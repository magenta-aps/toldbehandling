# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
import base64
from typing import Dict, List, Optional

from common.models import EboksBesked, IndberetterProfile
from django.contrib.auth.models import Group, User
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from ninja import Field, ModelSchema
from ninja.errors import ValidationError
from ninja.schema import Schema
from ninja.security import APIKeyHeader
from ninja_extra import api_controller, permissions, route
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.tokens import RefreshToken
from project.util import json_dump

# Django-ninja har endnu ikke understøttelse for PATCH med filer i multipart/form-data
# Se https://github.com/vitalik/django-ninja/pull/397
# Derfor laver vi alle skrivninger (POST og PATCH)  med application/json
# og fildata liggende som Base64-strenge i json-værdier.
#
# Hvis det kommer på plads, og vi ønsker at bruge multipart/form-data, skal
# In-skemaerne ændres til ikke at have filfeltet med, og metoderne der
# håndterer post og patch skal modtage filen som et File(...) argument:
#
# @foo_router.post("/", auth=get_auth_methods())
# def create_foo(self, payload: FooIn, filfeltnavn: ninja.File(...)):
#     item = Foo.objects.create(**payload.dict(), filfeltnavn=filfeltnavn)
#


class APIKeyAuth(APIKeyHeader):
    param_name = "X-API-Key"

    def authenticate(self, request, key):
        try:
            ib = IndberetterProfile.objects.get(api_key=key)
            request.user = ib.user
            return ib.user
        except IndberetterProfile.DoesNotExist:
            return None


def get_auth_methods():
    """This function defines the authentication methods available for this API."""
    return (JWTAuth(), APIKeyAuth())


class IndberetterProfileOut(ModelSchema):
    class Config:
        model = IndberetterProfile
        model_fields = ["cpr", "cvr", "api_key"]


class IndberetterProfileIn(ModelSchema):
    class Config:
        model = IndberetterProfile
        model_fields = ["cpr", "cvr"]


class UserOut(ModelSchema):
    groups: List[str]
    permissions: List[str]
    indberetter_data: Optional[IndberetterProfileOut] = Field(
        None, alias="indberetter_data"
    )

    class Config:
        model = User
        model_fields = ["username", "first_name", "last_name", "email", "is_superuser"]

    @staticmethod
    def resolve_groups(user: User):
        return [group.name for group in user.groups.all()]

    @staticmethod
    def resolve_permissions(user: User):
        return sorted(user.get_all_permissions())

    @staticmethod
    # https://github.com/vitalik/django-ninja/issues/350
    def resolve_indberetter_data(user: User):
        if hasattr(user, "indberetter_data"):
            return user.indberetter_data
        return None


class UserOutWithTokens(Schema):
    username: str
    first_name: str
    last_name: str
    email: Optional[str]
    is_superuser: bool
    groups: List[str]
    permissions: List[str]
    indberetter_data: Optional[IndberetterProfileOut] = Field(
        ..., alias="indberetter_data"
    )
    access_token: Optional[str]
    refresh_token: Optional[str]

    @staticmethod
    def user_to_dict(user: User) -> Dict:
        refresh_token = RefreshToken.for_user(user)
        return {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "is_superuser": user.is_superuser,
            "groups": [group.name for group in user.groups.all()],
            "permissions": sorted(user.get_all_permissions()),
            "indberetter_data": user.indberetter_data,
            "access_token": str(refresh_token.access_token),
            "refresh_token": str(refresh_token),
        }


class UserIn(ModelSchema):
    groups: List[str] = None
    indberetter_data: IndberetterProfileIn = None

    class Config:
        model = User
        model_fields = ["username", "first_name", "last_name", "email"]


@api_controller(
    "/user",
    tags=["User"],
    permissions=[permissions.IsAuthenticated],
)
class UserAPI:
    @route.get(
        "",
        response=UserOut,
        auth=get_auth_methods(),
        url_name="user_view",
    )
    def get_user(self, request):
        return request.user

    @route.get(
        "/cpr/{cpr}",
        response=UserOutWithTokens,
        auth=get_auth_methods(),
        url_name="user_cpr_get",
    )
    def get_user_cpr(self, cpr: int):
        user = get_object_or_404(User, indberetter_data__cpr=cpr)
        return UserOutWithTokens.user_to_dict(user)

    @route.post(
        "", response=UserOutWithTokens, auth=get_auth_methods(), url_name="user_create"
    )
    def create_user(self, payload: UserIn):
        try:
            groups = [Group.objects.get(name=g) for g in payload.groups]
        except Group.DoesNotExist:
            raise ValidationError("Group does not exist")
        user = User.objects.create(
            username=payload.username,
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            is_superuser=False,
        )
        user.groups.set(groups)
        IndberetterProfile.objects.create(
            user=user,
            cpr=payload.indberetter_data.cpr,
            cvr=payload.indberetter_data.cvr,
        )
        return UserOutWithTokens.user_to_dict(user)


class EboksBeskedIn(ModelSchema):
    afgiftsanmeldelse_id: int = None
    pdf: str  # base64

    class Config:
        model = EboksBesked
        model_fields = ["titel", "cpr", "cvr"]


@api_controller(
    "/eboks",
    tags=["Eboks"],
    permissions=[permissions.IsAuthenticated],
)
class EboksBeskedAPI:
    @route.post("", auth=get_auth_methods(), url_name="eboksbesked_create")
    def create_eboksbesked(self, payload: EboksBeskedIn):
        try:
            data = payload.dict()
            data["pdf"] = base64.b64decode(payload.pdf)
            item = EboksBesked.objects.create(**data)
            return {"id": item.id}
        except ValidationError as e:
            return HttpResponseBadRequest(
                json_dump(e.message_dict), content_type="application/json"
            )
