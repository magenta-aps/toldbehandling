# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import os
from typing import Union
from urllib import parse

from django.core.files import File
from django.template.defaultfilters import register
from django.utils.translation import gettext_lazy as _


@register.filter
def file_basename(item: Union[str, File]) -> str:
    if isinstance(item, File):
        item = item.name
    if isinstance(item, str):
        return unquote(os.path.basename(item))
    return ""


@register.filter
def zfill(item: Union[str, int], count: int) -> str:
    return str(item).zfill(count)


@register.filter
def godkendt(item: Union[bool, None]) -> str:
    if item is True:
        return _("Godkendt")
    elif item is False:
        return _("Afvist")
    else:
        return _("Ny")


@register.filter
def unquote(item: str) -> str:
    return parse.unquote(item)
