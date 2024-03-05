from typing import List, Optional

from common.api import get_auth_methods
from django.contrib.auth.models import User
from django_otp import verify_token
from django_otp.plugins.otp_totp.models import TOTPDevice
from ninja import ModelSchema
from ninja.filter_schema import FilterSchema
from ninja.params import Query
from ninja.schema import Schema
from ninja_extra import api_controller, permissions, route
from ninja_extra.exceptions import AuthenticationFailed
from ninja_jwt.controller import TokenObtainPairController, schema


class TOTPDeviceIn(ModelSchema):
    user_id: int

    class Config:
        model = TOTPDevice
        model_fields = [
            "key",
            "tolerance",
            "t0",
            "step",
            "drift",
            "digits",
            "name",
            "confirmed",
        ]


class TOTPDeviceOut(ModelSchema):
    user_id: int

    class Config:
        model = TOTPDevice
        model_fields = [
            "key",
            "tolerance",
            "t0",
            "step",
            "drift",
            "digits",
            "name",
            "confirmed",
        ]


class TOTPDeviceFilterSchema(FilterSchema):
    user: int


@api_controller(
    "/totpdevice",
    tags=["TOTPDevice"],
    permissions=[permissions.IsAuthenticated],
)
class TOTPDeviceAPI:
    @route.post("", auth=get_auth_methods(), url_name="totpdevice_create")
    # TODO: foretag tjeks så dette ikke kan misbruges
    def create(self, payload: TOTPDeviceIn):
        TOTPDevice.objects.create(**payload.dict())

    @route.get(
        "",
        response=List[TOTPDeviceOut],
        auth=get_auth_methods(),
        url_name="totpdevice_list",
    )
    def list(
        self,
        filters: TOTPDeviceFilterSchema = Query(...),
    ):
        return list(filters.filter(TOTPDevice.objects.all()))


#
# class TwoFactorLoginSchema(schema.obtain_pair_schema):
#     twofactor_token: str
#
#
# @api_controller('token/2fa', tags=['Auth'])
# class TwoFactorJWTController(TokenObtainPairController):
#     @route.post(
#         "",
#         response=schema.obtain_pair_schema.get_response_schema(),
#         url_name="token_obtain_pair",
#     )
#     def obtain_token(self, user_token: TwoFactorLoginSchema):
#         user_token.check_user_authentication_rule()
#         if user_token is None:
#             raise AuthenticationFailed("Missing token")
#         user = User.objects.get(username=user_token.username)
#         if not any([
#             verify_token(user, device.persistent_id, user_token.twofactor_token)
#             for device in TOTPDevice.objects.filter(user=user)
#         ]):
#             raise AuthenticationFailed("Token invalid")
#         return user_token.to_response_schema()


class TwoFactorLoginSchema(Schema):
    twofactor_token: str
    user_id: int


@api_controller("2fa/check", tags=["Auth"])
class TwoFactorLoginAPI:
    @route.post(
        "",
        response=bool,
        url_name="twofactor_check",
    )
    def check(self, user_token: TwoFactorLoginSchema):
        user = User.objects.get(id=user_token.user_id)
        if not any(
            [
                verify_token(user, device.persistent_id, user_token.twofactor_token)
                for device in TOTPDevice.objects.filter(user=user)
            ]
        ):
            raise AuthenticationFailed("Token invalid")
        return True
