from __future__ import annotations

import csv
from io import StringIO
from typing import Callable, Dict, Iterable, List, Union

from django.core.files.uploadedfile import UploadedFile
from openpyxl import load_workbook
from told_common.data import Vareafgiftssats, format_decimal, unformat_decimal


class SpreadsheetImportException(Exception):
    pass


class VareafgiftssatsSpreadsheetUtil:
    @staticmethod
    def spreadsheet_row(
        sats: Vareafgiftssats,
        headers: List[str],
        lookup_afgiftssats: Callable[[int], Vareafgiftssats],
    ) -> List[Union[str, int, bool]]:
        row = []
        for header in headers:
            value = getattr(sats, header, None)
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
                if (
                    value is not None
                    and header in VareafgiftssatsSpreadsheetUtil.header_map_in
                ):
                    value = VareafgiftssatsSpreadsheetUtil.header_map_in[header](value)
            except (TypeError, ValueError) as e:
                raise SpreadsheetImportException(f"Fejl ved import af regneark: {e}")
            data[header] = value
        return data

    @staticmethod
    def headers_unpretty(headers: Iterable[str]):
        return [
            header.replace(" ", "_").replace("(", "").replace(")", "").lower()
            for header in headers
        ]

    @staticmethod
    def load_csv(data: UploadedFile) -> List[Dict[str, Union[str, int, bool]]]:
        d = data.read().decode("utf-8")
        reader = csv.reader(StringIO(d), delimiter=",", quotechar='"')
        headers = next(reader)
        VareafgiftssatsSpreadsheetUtil.validate_headers(headers)
        headers = VareafgiftssatsSpreadsheetUtil.headers_unpretty(headers)
        satser = []
        for row in reader:
            satser.append(
                VareafgiftssatsSpreadsheetUtil.from_spreadsheet_row(headers, row)
            )
        return satser

    @staticmethod
    def load_xlsx(data: UploadedFile) -> List[Dict[str, Union[str, int, bool]]]:
        wb = load_workbook(data, data_only=True)
        sheet = wb.active
        values = sheet.values
        headers = next(values)
        VareafgiftssatsSpreadsheetUtil.validate_headers(headers)
        headers = VareafgiftssatsSpreadsheetUtil.headers_unpretty(headers)
        satser = []
        for row in values:
            satser.append(
                VareafgiftssatsSpreadsheetUtil.from_spreadsheet_row(headers, row)
            )
        return satser

    @staticmethod
    def validate_headers(headers):
        headers = set(headers)
        for expected_header in (
            "Afgiftsgruppenummer",
            "Overordnet",
            "Vareart (da)",
            "Vareart (kl)",
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
        # Start enumeration ved 2 fordi rækkerne i regneark er
        # 1-indekserede og vi har en header-række

        # Tjek at felter har gyldige værdier
        required = (
            "Afgiftsgruppenummer",
            "Vareart (da)",
            "Vareart (kl)",
            "Enhed",
            "Kræver indførselstilladelse",
        )
        for linje, vareafgiftssats in enumerate(satser, 2):
            for pretty, raw in zip(
                required, VareafgiftssatsSpreadsheetUtil.headers_unpretty(required)
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
                    # Start ved 2 fordi rækkerne i regneark er
                    # 1-indekserede og vi har en header-række
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
                    f"Afgiftssats med afgiftsgruppenummer "
                    f"{afgiftsgruppenummer} (linje {linje}) "
                    f"peger på overordnet "
                    f"{vareafgiftssats['overordnet']}, som ikke findes"
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
