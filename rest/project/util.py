import base64
from decimal import Decimal
from typing import Union, Dict, List

import orjson
from django.core.files import File
from django.http import HttpRequest
from ninja.renderers import BaseRenderer
from ninja_extra import permissions, ControllerBase


class ORJSONRenderer(BaseRenderer):
    media_type = "application/json"

    @staticmethod
    def default(o):
        if type(o) == Decimal:
            return str(o)
        if isinstance(o, File):
            with o.open("rb") as file:
                return base64.b64encode(file.read()).decode("utf-8")
        raise TypeError

    def render(self, request, data, *, response_status):
        return self.dumps(data)

    def dumps(self, data):
        return orjson.dumps(data, default=self.default)


def json_dump(data: Union[Dict, List]):
    return ORJSONRenderer().dumps(data)


class RestPermission(permissions.BasePermission):
    method_map = {
        "GET": "view",
        "POST": "add",
        "PATCH": "change",
    }

    def has_permission(self, request: HttpRequest, controller: ControllerBase) -> bool:
        return request.user.has_perm(
            f"{self.appname}.{self.method_map[request.method]}_{self.modelname}"
        )
