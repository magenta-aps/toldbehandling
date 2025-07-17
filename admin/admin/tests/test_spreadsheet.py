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
