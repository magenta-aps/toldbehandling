from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from functools import cached_property
from typing import Union, Optional

from dataclasses_json import dataclass_json
from django.template.defaultfilters import floatformat
from django.utils.translation import gettext_lazy as _


def format_decimal(decimal: Decimal) -> str:
    decimal = float(str(decimal))
    # if isinstance(decimal, str):
    #    decimal = float(decimal.replace(".", "").replace(",", "."))
    d = str(floatformat(text=decimal, arg=2))
    return d


def format_int(decimal: Union[Decimal, str]) -> int:
    return int(str(decimal).split(".")[0])


@dataclass_json
@dataclass
class Vareafgiftssats:
    id: int
    afgiftstabel: int
    vareart: str
    afgiftsgruppenummer: int
    enhed: str
    afgiftssats: Decimal
    kræver_indførselstilladelse: Optional[bool] = False
    minimumsbeløb: Optional[Decimal] = None
    overordnet: Optional[int] = None
    segment_nedre: Optional[Decimal] = None
    segment_øvre: Optional[Decimal] = None
    subsatser: Optional[list] = None

    class Enhed(Enum):
        SAMMENSAT = "sam"
        LITER = "l"
        ANTAL = "ant"
        KG = "kg"
        PROCENT = "pct"

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

        if self.enhed == Vareafgiftssats.Enhed.KG:
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
