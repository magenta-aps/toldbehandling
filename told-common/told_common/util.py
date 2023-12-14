import base64
import dataclasses
from typing import Any, Callable, Dict, Iterable, Optional, Union

from django.core.files import File
from django.core.serializers.json import DjangoJSONEncoder
from django.template.loader import render_to_string
from weasyprint import HTML
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
    template_name: str, context: dict, html_modifier: Optional[Callable] = None
) -> bytes:
    html = render_to_string(template_name, context)
    if callable(html_modifier):
        html = html_modifier(html)
    font_config = FontConfiguration()
    return HTML(string=html).write_pdf(font_config=font_config)


def join_words(words: Optional[str], separator: str = " "):
    return separator.join(filter(lambda word: word, words))


def opt_int(data: Union[str, int, None]):
    return int(data) if data is not None else None
