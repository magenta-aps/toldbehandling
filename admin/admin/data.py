from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from functools import cached_property
from typing import Union, Optional, List, Callable

from dataclasses_json import dataclass_json, config
from django.template.defaultfilters import floatformat
from django.utils.translation import gettext_lazy as _
from marshmallow import fields


def format_decimal(decimal: Decimal) -> str:
    decimal = float(str(decimal))
    # if isinstance(decimal, str):
    #    decimal = float(decimal.replace(".", "").replace(",", "."))
    d = str(floatformat(text=decimal, arg=2)) + ""
    return d


def format_int(decimal: Union[Decimal, str]) -> int:
    return int(str(decimal).split(".")[0])


@dataclass_json
@dataclass
class Vareafgiftssats:
    class Enhed(Enum):
        SAMMENSAT = "sam"
        LITER = "l"
        ANTAL = "ant"
        KILOGRAM = "kg"
        PROCENT = "pct"

    id: int
    afgiftstabel: int
    vareart: str
    afgiftsgruppenummer: int
    enhed: Enhed
    afgiftssats: Decimal
    kræver_indførselstilladelse: Optional[bool] = False
    minimumsbeløb: Optional[Decimal] = None
    overordnet: Optional[int] = None
    segment_nedre: Optional[Decimal] = None
    segment_øvre: Optional[Decimal] = None
    subsatser: Optional[list] = None

    @cached_property
    def text(self) -> str:
        afgiftssats = format_decimal(self.afgiftssats)
        segment_nedre = self.segment_nedre
        segment_øvre = self.segment_øvre

        if self.enhed == Vareafgiftssats.Enhed.SAMMENSAT and self.subsatser:
            return " + ".join([subsats.text for subsats in self.subsatser])

        if self.enhed == Vareafgiftssats.Enhed.LITER:
            if segment_øvre and segment_nedre:
                return _(
                    "{kr} kr. pr liter mellem {nedre} liter og {øvre} liter"
                ).format(
                    kr=afgiftssats,
                    nedre=format_decimal(segment_nedre),
                    øvre=format_decimal(segment_øvre),
                )
            if segment_øvre:
                return _("{kr} kr. pr liter under {øvre} liter").format(
                    kr=afgiftssats, øvre=format_decimal(segment_øvre)
                )
            if segment_nedre:
                return _("{kr} kr. pr liter over {nedre} liter").format(
                    kr=afgiftssats, nedre=format_decimal(segment_nedre)
                )
            return _("{kr} kr. pr liter").format(kr=afgiftssats)

        if self.enhed == Vareafgiftssats.Enhed.KILOGRAM:
            if segment_øvre and segment_nedre:
                return _("{kr} kr. pr kg mellem {nedre} kg og {øvre} kg").format(
                    kr=afgiftssats,
                    nedre=format_decimal(segment_nedre),
                    øvre=format_decimal(segment_øvre),
                )
            if segment_øvre:
                return _("{kr} kr. pr kg under {øvre} kg").format(
                    kr=afgiftssats, øvre=format_decimal(segment_øvre)
                )
            if segment_nedre:
                return _("{kr} kr. pr kg over {nedre} kg").format(
                    kr=afgiftssats, nedre=format_decimal(segment_nedre)
                )
            return _("{kr} kr. pr kg").format(kr=afgiftssats)

        if self.enhed == Vareafgiftssats.Enhed.ANTAL:
            if segment_øvre and segment_nedre:
                return _("{kr} kr. pr stk mellem {nedre} stk og {øvre} stk").format(
                    kr=afgiftssats,
                    nedre=format_int(segment_nedre),
                    øvre=format_int(segment_øvre),
                )
            if segment_øvre:
                return _("{kr} kr. pr stk under {øvre} stk").format(
                    kr=afgiftssats, øvre=format_int(segment_øvre)
                )
            if segment_nedre:
                return _("{kr} kr. pr stk over {nedre} stk").format(
                    kr=afgiftssats, nedre=format_int(segment_nedre)
                )
            return _("{kr} kr. pr stk").format(kr=afgiftssats)

        if self.enhed == Vareafgiftssats.Enhed.PROCENT:
            if segment_øvre and segment_nedre:
                return _("{pct}% af fakturabeløb mellem {nedre} og {øvre}").format(
                    pct=afgiftssats,
                    nedre=format_decimal(segment_nedre),
                    øvre=format_decimal(segment_øvre),
                )
            if segment_øvre:
                return _("{pct}% af fakturabeløb under {øvre}").format(
                    pct=afgiftssats, øvre=format_decimal(segment_øvre)
                )
            if segment_nedre:
                return _("{pct}% af fakturabeløb over {nedre}").format(
                    pct=afgiftssats, nedre=format_decimal(segment_nedre)
                )
            return _("{pct}% af fakturabeløb").format(pct=afgiftssats)

    def populate_subs(self, sub_getter: Callable[[int], List[Vareafgiftssats]]) -> None:
        if self.enhed == Vareafgiftssats.Enhed.SAMMENSAT:
            subs = sub_getter(self.id)
            if len(subs) > 0:
                self.subsatser = []
                for subsats in subs:
                    self.subsatser.append(subsats)

    def spreadsheet_row(
        self, headers: List[str], lookup_afgiftssats: Callable[[int], Vareafgiftssats]
    ) -> List[Union[str, int, bool]]:
        row = []
        for header in headers:
            value = getattr(self, header, None)
            if value is not None:
                if header == "overordnet":
                    value = lookup_afgiftssats(value).afgiftsgruppenummer
                elif header in (
                    "afgiftssats",
                    "minimumsbeløb",
                    "segment_øvre",
                    "segment_nedre",
                ):
                    value = format_decimal(value)
                elif header == "kræver_indførselstilladelse":
                    value = "ja" if value else "nej"
                elif header == "enhed":
                    value = value.name.lower()
            row.append(value)
        return row


def encode_optional_isoformat(d):
    if d is None:
        return None
    return d.isoformat()


@dataclass_json
@dataclass
class Afgiftstabel:
    id: int
    kladde: bool
    gyldig_fra: Optional[date] = field(
        metadata=config(
            encoder=encode_optional_isoformat,
            decoder=date.fromisoformat,
            mm_field=fields.Date(format="iso"),
        ),
        default=None,
    )
    gyldig_til: Optional[date] = field(
        metadata=config(
            encoder=encode_optional_isoformat,
            decoder=date.fromisoformat,
            mm_field=fields.Date(format="iso"),
        ),
        default=None,
    )
    vareafgiftssatser: Optional[List[Vareafgiftssats]] = None
