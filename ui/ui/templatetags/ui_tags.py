import os
from typing import Union

from django.template.defaultfilters import register


@register.filter
def file_basename(item: str) -> str:
    return os.path.basename(item)


@register.filter
def zfill(item: Union[str, int], count: int) -> str:
    return str(item).zfill(count)
