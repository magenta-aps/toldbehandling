from datetime import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase
from told_common.form_mixins import DateTimeInput, FixedWidthIntegerField


class FixedWidthIntegerFieldTest(TestCase):
    def test_to_python_raises_validation_error_on_invalid_input(self):
        field = FixedWidthIntegerField(width=3, min_value=0)

        with self.assertRaises(ValidationError) as cm:
            field.to_python("abc")  # non-integer input triggers ValueError

        self.assertEqual(cm.exception.code, "invalid")
        self.assertIn("Indtast et heltal", str(cm.exception.message))


class DateTimeInputTest(TestCase):
    def test_datetime_input_renders_with_correct_format(self):
        mixin = DateTimeInput()
        self.assertEqual(mixin.format, "%Y-%m-%dT%H:%M:%S")
        self.assertEqual(mixin.input_type, "datetime-local")

    def test_datetime_input_formatting(self):
        mixin = DateTimeInput()
        dt = datetime(2025, 7, 18, 15, 30, 45)
        rendered = mixin.format_value(dt)
        self.assertEqual(rendered, "2025-07-18T15:30:45")
