# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0


from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from admin.spreadsheet import SpreadsheetImportException, VareafgiftssatsSpreadsheetUtil


class VareafgiftssatsSpreadsheetUtilTest(TestCase):
    def test_from_spreadsheet_row_idx_error(self):
        result = VareafgiftssatsSpreadsheetUtil.from_spreadsheet_row(
            headers=["Afgiftsgruppenummer", "Vareart (da)"], row=[1337]
        )

        # If an IndexError occurs, the value will be set to None
        self.assertEqual(result, {"afgiftsgruppenummer": 1337, "vareart_da": None})

    def test_from_spreadsheet_row_invalid_value(self):
        with self.assertRaises(SpreadsheetImportException):
            _ = VareafgiftssatsSpreadsheetUtil.from_spreadsheet_row(
                headers=["Afgiftsgruppenummer", "Vareart (da)"],
                row=["invalid int here", "Fancy stuff"],
            )

    def test_validate_satser_import_exception(self):
        with self.assertRaises(SpreadsheetImportException):
            _ = VareafgiftssatsSpreadsheetUtil.validate_satser(
                satser=[{"afgiftsgruppenummer": None}]
            )


class VareafgiftssatsSpreadsheetUtilTest(TestCase):
    def test_load_csv_handles_missing_columns(self):
        # Create CSV content with headers, and one row with missing values
        csv_content = (
            "Afgiftsgruppenummer,Overordnet,Vareart (da),Vareart (kl),Enhed,Afgiftssats,Kræver indførselstilladelse,Har privat tillægsafgift alkohol,Synlig for private,Minimumsbeløb,Segment nedre,Segment øvre\n"
            "1001,1000,Øl,Ol,liter,2.5,ja,nej,ja,10,1.0,5.0\n"
            "1002,1000,Vin,Vin,liter,2.5,ja,nej\n"  # Missing last 4 columns
        )

        uploaded_file = SimpleUploadedFile("satser.csv", csv_content.encode("utf-8"))

        satser = VareafgiftssatsSpreadsheetUtil.load_csv(uploaded_file)

        self.assertEqual(len(satser), 2)

        # Check that missing values are interpreted as None
        second_row = satser[1]
        self.assertEqual(second_row["afgiftsgruppenummer"], 1002)
        self.assertIsNone(second_row.get("minimumsbeløb"))
        self.assertIsNone(second_row.get("segment_nedre"))
        self.assertIsNone(second_row.get("segment_øvre"))

    @patch(
        "admin.spreadsheet.VareafgiftssatsSpreadsheetUtil.validate_headers",
        lambda x: None,
    )
    def test_load_csv_raises_on_invalid_parser(self):
        # Afgiftsgruppenummer should be an int, but "INVALID" is not parsable
        csv_content = (
            "Afgiftsgruppenummer,Overordnet,Vareart (da),Vareart (kl),Enhed,Afgiftssats,Kræver indførselstilladelse,Har privat tillægsafgift alkohol,Synlig for private,Minimumsbeløb,Segment nedre,Segment øvre\n"
            "INVALID,1000,Øl,Ol,l,2.5,ja,nej,ja,10,1.0,5.0\n"
        )
        uploaded_file = SimpleUploadedFile(
            "satser_invalid.csv", csv_content.encode("utf-8")
        )

        with self.assertRaises(SpreadsheetImportException) as ctx:
            VareafgiftssatsSpreadsheetUtil.load_csv(uploaded_file)

        self.assertIn("Fejl ved import af regneark", str(ctx.exception))
        self.assertIn(
            "invalid literal", str(ctx.exception).lower()
        )  # part of ValueError message
