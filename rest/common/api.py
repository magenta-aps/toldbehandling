# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
# mypy: disable-error-code="call-arg, attr-defined"
import base64
import re
from typing import Annotated, Dict, List, Optional, Union

from common.models import EboksBesked, IndberetterProfile
from django.contrib.auth.models import Group, User
from django.core.exceptions import BadRequest
from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django_otp.plugins.otp_totp.models import TOTPDevice
from ninja import Field, ModelSchema
from ninja.errors import ValidationError
from ninja.filter_schema import FilterSchema
from ninja.params import Query
from ninja.schema import Schema
from ninja.security import APIKeyHeader
from ninja_extra import ControllerBase, api_controller, paginate, permissions, route
from ninja_extra.exceptions import PermissionDenied
from ninja_extra.schemas import NinjaPaginationResponseSchema
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.tokens import RefreshToken

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


class DjangoPermission(permissions.BasePermission):
    def __init__(self, permission: str) -> None:
        self._permission = permission

    def has_permission(self, request: HttpRequest, controller: ControllerBase):
        return request.user.has_perm(self._permission)


def get_auth_methods():
    """This function defines the authentication methods available for this API."""
    return (JWTAuth(), APIKeyAuth())


class IndberetterProfileOut(ModelSchema):
    class Config:
        model = IndberetterProfile
        model_fields = ["cvr"]


class IndberetterProfileApiKeyOut(ModelSchema):
    class Config:
        model = IndberetterProfile
        model_fields = ["api_key"]


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
    twofactor_enabled: bool

    class Config:
        model = User
        model_fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_superuser",
        ]

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

    @staticmethod
    def resolve_twofactor_enabled(user: User) -> bool:
        return TOTPDevice.objects.filter(user=user).exists()


class UserOutWithTokens(Schema):
    id: int
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
            "id": user.pk,
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
    groups: Optional[List[str]] = None
    indberetter_data: Optional[IndberetterProfileIn] = None

    class Config:
        model = User
        model_fields = ["username", "first_name", "last_name", "email"]


class UserFilterSchema(FilterSchema):
    username: Annotated[Optional[str], Field(None, q="username__icontains")]
    username_startswith: Annotated[
        Optional[str], Field(None, q="username__istartswith")
    ]
    first_name: Annotated[Optional[str], Field(None, q="first_name__icontains")]
    last_name: Annotated[Optional[str], Field(None, q="last_name__icontains")]
    email: Annotated[Optional[str], Field(None, q="email__icontains")]
    is_superuser: Optional[bool] = None
    group: Annotated[Optional[str], Field(None, q="groups__name__icontains")]


@api_controller(
    "/user",
    tags=["User"],
    permissions=[permissions.IsAuthenticated],
)
class UserAPI:
    def check_user(self, item: User):
        if not self.filter_user(User.objects.filter(id=item.id)).exists():
            raise PermissionDenied

    def filter_user(self, qs: QuerySet) -> QuerySet:
        user = self.context.request.user
        if user.is_superuser:
            return qs
        if user.has_perm("auth.view_user"):
            return qs
        return qs.filter(pk=user.pk)

    def dash_null(self, key: str, value: Union[int, str]):
        if value == "-":
            return {key + "__isnull": True}
        if type(value) is str:
            try:
                value = int(value)
            except ValueError:
                raise BadRequest(f"Incorrect value '{value}', must be '-' or a number")
        return {key: value}

    @route.get(
        "/this",
        response=UserOut,
        auth=get_auth_methods(),
        url_name="user_view",
    )
    def get_user_from_request(self, request):
        return request.user

    @route.get(
        "/cpr/{cpr}",
        response=UserOutWithTokens,
        auth=get_auth_methods(),
        url_name="user_cpr_get",
    )
    def get_user_cpr(self, cpr: int):
        return self.get_user(cpr, "-")

    @route.get(
        "/{cpr}/{cvr}",
        response=UserOutWithTokens,
        auth=get_auth_methods(),
        url_name="user_get",
    )
    def get_user(self, cpr: int, cvr: Union[int, str]):
        user = get_object_or_404(
            User,
            **{
                "indberetter_data__cpr": cpr,
                **self.dash_null("indberetter_data__cvr", cvr),
            },
        )
        self.check_user(user)
        return UserOutWithTokens.user_to_dict(user)

    @route.get(
        "/cpr/{cpr}/apikey",
        response=IndberetterProfileApiKeyOut,
        auth=JWTAuth(),
        url_name="user_get_cpr_apikey",
        permissions=[DjangoPermission("auth.read_apikeys")],
    )
    def get_user_cpr_apikey(self, cpr: int):
        return self.get_user_apikey(cpr, "-")

    @route.get(
        "/{cpr}/{cvr}/apikey",
        response=IndberetterProfileApiKeyOut,
        auth=JWTAuth(),
        url_name="user_get_apikey",
        permissions=[DjangoPermission("auth.read_apikeys")],
    )
    def get_user_apikey(self, cpr: int, cvr: Union[int, str]):
        user = get_object_or_404(
            User,
            **{
                "indberetter_data__cpr": cpr,
                **self.dash_null("indberetter_data__cvr", cvr),
            },
        )
        self.check_user(user)
        return user.indberetter_data

    @route.post(
        "", response=UserOutWithTokens, auth=get_auth_methods(), url_name="user_create"
    )
    def create_user(self, payload: UserIn):
        try:
            groups = [Group.objects.get(name=g) for g in payload.groups or []]
        except Group.DoesNotExist:
            raise ValidationError("Group does not exist")  # type: ignore

        username = payload.username
        if User.objects.filter(username=username).exists():
            matcher: re.Pattern = re.compile("^" + re.escape(username) + r" \((\d+)\)$")
            existing_usernames = sorted(
                filter(
                    lambda u: matcher.match(u) is not None,
                    User.objects.filter(username__startswith=username).values_list(
                        "username", flat=True
                    ),
                )
            )
            index = 0
            if len(existing_usernames) > 0:
                match = re.search(matcher, existing_usernames[-1])
                if match is not None:
                    index = int(match.group(1))
            username = f"{username} ({index+1})"

        user = User.objects.create(
            username=username,
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            is_superuser=False,
        )
        user.groups.set(groups)
        if payload.indberetter_data:
            IndberetterProfile.objects.create(
                user=user,
                cpr=payload.indberetter_data.cpr,
                cvr=payload.indberetter_data.cvr,
                api_key=IndberetterProfile.create_api_key(),
            )
        else:
            raise ValidationError("indberetter_data does not exist")  # type: ignore

        return UserOutWithTokens.user_to_dict(user)

    @route.get(
        "",
        response=NinjaPaginationResponseSchema[UserOut],
        auth=get_auth_methods(),
        url_name="user_list",
    )
    @paginate()  # https://eadwincode.github.io/django-ninja-extra/tutorial/pagination/
    def list(self, filters: UserFilterSchema = Query(...)):  # type: ignore
        return list(filters.filter(User.objects.all().order_by("id")))

    @route.patch(
        "/cpr/{cpr}",
        response=UserOutWithTokens,
        auth=get_auth_methods(),
        url_name="user_cpr_update",
    )
    def update_by_cpr(self, cpr: int, payload: UserIn):
        return self.update(cpr, "-", payload)

    @route.patch(
        "/{cpr}/{cvr}",
        response=UserOutWithTokens,
        auth=get_auth_methods(),
        url_name="user_update",
    )
    def update(self, cpr: int, cvr: Union[int, str], payload: UserIn):
        cpr = int(cpr)
        item = get_object_or_404(
            User,
            **{
                "indberetter_data__cpr": cpr,
                **self.dash_null("indberetter_data__cvr", cvr),
            },
        )
        user = self.context.request.user
        if not (
            user.has_perm("auth.change_user")
            or (
                hasattr(user, "indberetter_data")
                and user.indberetter_data
                and user.indberetter_data.cpr == cpr
            )
        ):
            raise PermissionDenied
        if payload.groups is not None and not user.has_perm("auth.change_user"):
            raise PermissionDenied
        if payload.groups is not None:
            try:
                groups = [Group.objects.get(name=g) for g in payload.groups or []]
                item.groups.set(groups)
            except Group.DoesNotExist:
                raise ValidationError("Group does not exist")  # type: ignore
        if payload.username:
            item.username = payload.username
        if payload.first_name is not None:
            item.first_name = payload.first_name
        if payload.last_name is not None:
            item.last_name = payload.last_name
        if payload.email is not None:
            item.email = payload.email
        item.save()
        if payload.indberetter_data:
            item.indberetter_data.cvr = payload.indberetter_data.cvr
        item.indberetter_data.save()
        return UserOutWithTokens.user_to_dict(item)

    @route.patch(
        "/{id}",
        response=UserOutWithTokens,
        auth=get_auth_methods(),
        url_name="user_update_by_id",
    )
    def update_by_id(self, id: int, payload: UserIn):
        user_signedin = self.context.request.user
        user = get_object_or_404(User, id=id)

        # User may not change other users, unless they have class access
        if user_signedin.id != user.id and not user_signedin.has_perm(
            "auth.change_user"
        ):
            raise PermissionDenied

        # User may not change their own groups
        user_groups = None
        if payload.groups is not None:
            groups = set(payload.groups)
            if (
                payload.groups is not None
                and groups != set(user.groups.all().values_list("name", flat=True))
                and not user_signedin.has_perm("auth.change_user")
            ):
                raise PermissionDenied
            try:
                user_groups = [Group.objects.get(name=g) for g in groups]
            except Group.DoesNotExist:
                raise ValidationError("Group does not exist")  # type: ignore

        user.username = payload.username
        user.first_name = payload.first_name
        user.last_name = payload.last_name
        user.email = payload.email
        user.save()

        if user_groups is not None:
            user.groups.set(user_groups)

        if payload.indberetter_data:
            if payload.indberetter_data.cpr:
                user.indberetter_data.cpr = payload.indberetter_data.cpr

            if payload.indberetter_data.cvr:
                user.indberetter_data.cvr = payload.indberetter_data.cvr

            user.indberetter_data.save()

        return UserOutWithTokens.user_to_dict(user)


class EboksBeskedIn(ModelSchema):
    afgiftsanmeldelse_id: Optional[int] = None
    privat_afgiftsanmeldelse_id: Optional[int] = None
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
        data = payload.dict()
        data["pdf"] = base64.b64decode(payload.pdf)
        item = EboksBesked.objects.create(**data)
        return {"id": item.id}
