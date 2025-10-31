import base64
import dataclasses
import hashlib
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from enum import Enum
from functools import partial
from typing import Any, BinaryIO, Callable, Dict, Iterable, Optional, Union

import holidays
from django.contrib.staticfiles.finders import find as find_staticfile
from django.core.cache import cache
from django.core.files import File
from django.core.serializers.json import DjangoJSONEncoder
from django.http import QueryDict
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.utils import translation
from pypdf import PdfWriter
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration


def filter_dict_values(data: Dict[Any, Any], values_to_trim: Iterable):
    return dict(filter(lambda pair: pair[1] not in values_to_trim, data.items()))


def filter_dict_none(data: Dict[Any, Any]):
    return filter_dict_values(data, (None,))


def get_file_base64(file: File):
    with file.open("rb") as file:
        return base64.b64encode(file.read()).decode("utf-8")


# Copied from core python because its containing module `distutils` is deprecated.
def strtobool(val):
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return 1
    elif val in ("n", "no", "f", "false", "off", "0"):
        return 0
    else:
        raise ValueError("invalid truth value %r" % (val,))


class JSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)


def cast_or_none(dest_class, value):
    return dest_class(value) if value is not None else None


def render_pdf(
    template_name: str,
    context: dict,
    html_modifier: Optional[Callable] = None,
    stylesheets=None,
) -> bytes:
    # Late import to avoid circular import (this file is loaded by the Django settings
    # machinery which in turn is activated if we import `django_libsass` at the top
    # level of this module.)
    import django_libsass

    html = render_to_string(template_name, context)
    if callable(html_modifier):
        html = html_modifier(html)
    font_config = FontConfiguration()

    stylesheet_objs = []
    if stylesheets:
        for filename in stylesheets:
            if filename.endswith(".scss"):
                # Compile SCSS to CSS
                output = django_libsass.compile(
                    filename=find_staticfile(filename),
                    output_style=django_libsass.OUTPUT_STYLE,
                    source_comments=django_libsass.SOURCE_COMMENTS,
                )
                stylesheet_objs.append(CSS(string=output))
            else:
                # Use CSS file as-is
                stylesheet_objs.append(CSS(filename=find_staticfile(filename)))

    return HTML(string=html).write_pdf(
        font_config=font_config, stylesheets=stylesheet_objs
    )


class language:
    def __init__(self, new_lang):
        self.new_lang = new_lang
        self.old_lang = translation.get_language()

    def __enter__(self):
        translation.activate(self.new_lang)

    def __exit__(self, type, value, tb):
        translation.activate(self.old_lang)


def join_words(words: list[str], separator: str = " "):
    return separator.join(filter(lambda word: word, words))


def opt_int(data: Union[str, int, None]):
    return int(data) if data is not None else None


def opt_str(data: Union[str, int, None]):
    return str(data) if data is not None else None


def date_next_workdays(from_date: date, add_days: int):
    key = f"{from_date.isoformat()}|{add_days}"
    if key in cache:
        return cache.get(key)
    business_days_to_add = add_days
    current_date = from_date
    holiday_list = holidays.country_holidays("DK")
    while business_days_to_add > 0:
        current_date += timedelta(days=1)
        if current_date.weekday() >= 5 or current_date in holiday_list:
            continue
        business_days_to_add -= 1
    cache.set(key, current_date, 24 * 60 * 60)
    return current_date


def round_decimal(d: Decimal, rounding: str = ROUND_HALF_EVEN):
    return Decimal(d.quantize(Decimal(".01"), rounding=rounding))


def _asdict_factory(data):
    def convert_value(obj):
        if isinstance(obj, Enum):
            return obj.value
        return obj

    return dict((k, convert_value(v)) for k, v in data)


def dataclass_map_to_dict(data: Dict):
    return {
        key: dataclasses.asdict(value, dict_factory=_asdict_factory)
        for key, value in data.items()
    }


def write_pdf(output_path, *inputs: BinaryIO):
    writer = PdfWriter()
    for input in inputs:
        writer.append(input)
    with open(output_path, "wb") as output:
        writer.write(output)


def format_daterange(start: date, end: date, sep: str = " - "):
    range_parts = []
    if not start and not end:
        range_parts.append("altid")
    else:
        if start:
            range_parts.append(start.isoformat())
        else:
            range_parts.append("al fortid")
        if end:
            range_parts.append(end.isoformat())
        else:
            range_parts.append("al fremtid")
    return sep.join(range_parts)


def join(delimiter: Union[str, int], items: Iterable[Union[Any]]):
    return str(delimiter).join([str(x) for x in items])


def tf5_common_context() -> dict:
    return {
        "hide_api_key_btn": True,
    }


# Samme som item[key1][key2][key3] ...
# men giver ikke KeyError hvis en key ikke findes
# eller ValueError hvis et af leddene er None i stedet for en dict
# Der returneres enten den ønskede værdi eller None
def lenient_get(item, *keys: str):
    for key in keys:
        if item is not None:
            item = item.get(key)
    return item


def multivaluedict_to_querydict(multivaluedict: Optional[dict[str, list]]) -> QueryDict:
    query_dict = QueryDict(mutable=True)
    if multivaluedict is not None:
        for key in multivaluedict:
            query_dict.setlist(key, multivaluedict[key])
    return query_dict


def hash_file(file):
    hasher = hashlib.md5()
    for buf in iter(partial(file.read, 65536), b""):
        hasher.update(buf)
    return hasher.hexdigest()
