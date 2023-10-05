# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from decimal import Context, Decimal
from enum import Enum
from functools import cached_property
from io import StringIO
from typing import Callable, Dict, Iterable, List, Optional, Union

from dataclasses_json import config, dataclass_json
from django.core.files.uploadedfile import UploadedFile
from django.template.defaultfilters import floatformat
from django.utils.translation import gettext_lazy as _
from marshmallow import fields
from openpyxl import load_workbook

from admin.exceptions import SpreadsheetImportException


def format_decimal(decimal: Decimal) -> str:
    decimal = float(str(decimal))
    # if isinstance(decimal, str):
    #    decimal = float(decimal.replace(".", "").replace(",", "."))
    d = str(floatformat(text=decimal, arg=2)) + ""
    return d


def unformat_decimal(string: str) -> Optional[Decimal]:
    if string in (None, ""):
        return None
    return Decimal(string.replace(".", "").replace(",", "."), context=Context(prec=2))


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
            if subs is not None and len(subs) > 0:
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

    header_map_in = {
        "overordnet": int,
        "afgiftsgruppenummer": int,
        "kræver_indførselstilladelse": lambda value: value.lower() in ("ja", "aap"),
        "afgiftssats": unformat_decimal,
        "minimumsbeløb": unformat_decimal,
        "segment_øvre": unformat_decimal,
        "segment_nedre": unformat_decimal,
        "enhed": lambda value: getattr(Vareafgiftssats.Enhed, value.upper()).value,
    }

    @staticmethod
    def from_spreadsheet_row(
        headers: List[str], row: List[Union[str, int, bool]]
    ) -> Dict[str, Union[str, int, bool]]:
        data = {}
        for i, header in enumerate(headers):
            header = header.lower()
            try:
                value = row[i]
            except IndexError:
                value = None
            if value == "":
                value = None
            try:
                if value is not None and header in Vareafgiftssats.header_map_in:
                    value = Vareafgiftssats.header_map_in[header](value)
            except (TypeError, ValueError) as e:
                raise SpreadsheetImportException(f"Fejl ved import af regneark: {e}")
            data[header] = value
        return data

    @staticmethod
    def headers_unpretty(headers: Iterable[str]):
        return [header.replace(" ", "_").lower() for header in headers]

    @staticmethod
    def load_csv(data: UploadedFile) -> List[Dict[str, Union[str, int, bool]]]:
        d = data.read().decode("utf-8")
        reader = csv.reader(StringIO(d), delimiter=",", quotechar='"')
        headers = next(reader)
        Vareafgiftssats.validate_headers(headers)
        headers = Vareafgiftssats.headers_unpretty(headers)
        satser = []
        for row in reader:
            satser.append(Vareafgiftssats.from_spreadsheet_row(headers, row))
        return satser

    @staticmethod
    def load_xlsx(data: UploadedFile) -> List[Dict[str, Union[str, int, bool]]]:
        wb = load_workbook(data, data_only=True)
        sheet = wb.active
        values = sheet.values
        headers = next(values)
        Vareafgiftssats.validate_headers(headers)
        headers = Vareafgiftssats.headers_unpretty(headers)
        satser = []
        for row in values:
            satser.append(Vareafgiftssats.from_spreadsheet_row(headers, row))
        return satser

    @staticmethod
    def validate_headers(headers):
        headers = set(headers)
        for expected_header in (
            "Afgiftsgruppenummer",
            "Overordnet",
            "Vareart",
            "Enhed",
            "Afgiftssats",
            "Kræver indførselstilladelse",
            "Minimumsbeløb",
            "Segment nedre",
            "Segment øvre",
        ):
            if expected_header not in headers:
                raise SpreadsheetImportException(
                    f"Mangler kolonne med {expected_header}"
                )

    @staticmethod
    def validate_satser(satser: List[Dict[str, Union[str, int, bool]]]):
        # Start enumeration ved 2 fordi rækkerne i regneark er 1-indekserede og vi har en header-række

        # Tjek at felter har gyldige værdier
        required = (
            "Afgiftsgruppenummer",
            "Vareart",
            "Enhed",
            "Kræver indførselstilladelse",
        )
        for linje, vareafgiftssats in enumerate(satser, 2):
            for pretty, raw in zip(
                required, Vareafgiftssats.headers_unpretty(required)
            ):
                if vareafgiftssats[raw] is None:
                    raise SpreadsheetImportException(
                        f'Mangler felt "{pretty}" på linje {linje}'
                    )

        # Tjek at afgiftsgruppenummer er unikt
        afgiftsgruppenumre = set()
        for linje, vareafgiftssats in enumerate(satser, 2):
            afgiftsgruppenummer = vareafgiftssats["afgiftsgruppenummer"]
            if afgiftsgruppenummer in afgiftsgruppenumre:
                linjenumre = [
                    # Start ved 2 fordi rækkerne i regneark er 1-indekserede og vi har en header-række
                    str(i)
                    for i, sats in enumerate(satser, 2)
                    if sats["afgiftsgruppenummer"] == afgiftsgruppenummer
                ]
                raise SpreadsheetImportException(
                    f"Afgiftsgruppenummer {afgiftsgruppenummer} optræder to gange "
                    f"(linjer: {', '.join(linjenumre)})"
                )
            afgiftsgruppenumre.add(vareafgiftssats["afgiftsgruppenummer"])

        by_afgiftsgruppenummer = {
            x["afgiftsgruppenummer"]: (x, i) for i, x in enumerate(satser, 2)
        }

        # Tjek at alle satser der peges på med "overordnet" eksisterer
        for linje, vareafgiftssats in enumerate(satser, 2):
            afgiftsgruppenummer = vareafgiftssats["afgiftsgruppenummer"]
            if (
                vareafgiftssats["overordnet"]
                and vareafgiftssats["overordnet"] not in afgiftsgruppenumre
            ):
                raise SpreadsheetImportException(
                    f"Afgiftssats med afgiftsgruppenummer {afgiftsgruppenummer} (linje {linje}) "
                    f"peger på overordnet {vareafgiftssats['overordnet']}, som ikke findes"
                )
            overordnet_id: int = vareafgiftssats["overordnet"]
            besøgt = set()
            while overordnet_id is not None:
                linje = by_afgiftsgruppenummer[afgiftsgruppenummer][1]
                if afgiftsgruppenummer == overordnet_id:
                    raise SpreadsheetImportException(
                        f"Vareafgiftssats {afgiftsgruppenummer} (linje {linje}) "
                        f"peger på sig selv som overordnet"
                    )
                if overordnet_id in besøgt:
                    overordnet_linje = by_afgiftsgruppenummer[overordnet_id][1]
                    raise SpreadsheetImportException(
                        f"Vareafgiftssats {afgiftsgruppenummer} (linje {linje}) "
                        f"har {overordnet_id} (linje {overordnet_linje}) "
                        f"som overordnet, men {overordnet_id} har også "
                        f"{afgiftsgruppenummer} i kæden af overordnede"
                    )
                besøgt.add(afgiftsgruppenummer)
                afgiftsgruppenummer = overordnet_id
                overordnet_id = by_afgiftsgruppenummer[afgiftsgruppenummer][0][
                    "overordnet"
                ]


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
