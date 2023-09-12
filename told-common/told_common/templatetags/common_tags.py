import os
from typing import Union
from urllib import parse

from django.template.defaultfilters import register
from django.utils.translation import gettext_lazy as _


@register.filter
def file_basename(item: str) -> str:
    return os.path.basename(item)


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
