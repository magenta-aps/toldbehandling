# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import base64
from decimal import Decimal
from typing import Dict, List, Union

import orjson
from django.core.exceptions import ValidationError
from django.core.files import File
from django.http import HttpRequest
from ninja.renderers import BaseRenderer
from ninja_extra import ControllerBase, permissions


class ORJSONRenderer(BaseRenderer):
    media_type = "application/json"

    @staticmethod
    def default(o):
        if type(o) is Decimal:
            return str(o)
        if isinstance(o, File):
            with o.open("rb") as file:
                return base64.b64encode(file.read()).decode("utf-8")
        if isinstance(o, ValidationError):
            if hasattr(o, "message"):
                return str(o.message)
            if hasattr(o, "error_dict"):
                return o.error_dict
            else:
                return o.error_list

        raise TypeError

    def render(self, request, data, *, response_status):
        return self.dumps(data)

    def dumps(self, data):
        return orjson.dumps(data, default=self.default)


def json_dump(data: Union[Dict, List, ValidationError]):
    return ORJSONRenderer().dumps(data)


class RestPermission(permissions.BasePermission):
    method_map = {
        "GET": "view",
        "POST": "add",
        "PATCH": "change",
        "DELETE": "delete",
    }
    appname: str
    modelname: str

    def has_permission(self, request: HttpRequest, controller: ControllerBase) -> bool:
        method = str(request.method)
        operation = self.method_map[method]
        return request.user.has_perm(f"{self.appname}.{operation}_{self.modelname}")


# Copied from core python because its containing module `distutils` is deprecated.
def strtobool(val):
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return 1
    elif val in ("n", "no", "f", "false", "off", "0"):
        return 0
    else:
        raise ValueError("invalid truth value %r" % (val,))
