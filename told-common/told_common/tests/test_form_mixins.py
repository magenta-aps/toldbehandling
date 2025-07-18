from django.core.exceptions import ValidationError
from django.test import TestCase
from told_common.form_mixins import FixedWidthIntegerField


class FixedWidthIntegerFieldTest(TestCase):
    def test_to_python_raises_validation_error_on_invalid_input(self):
        field = FixedWidthIntegerField(width=3, min_value=0)

        with self.assertRaises(ValidationError) as cm:
            field.to_python("abc")  # non-integer input triggers ValueError

        self.assertEqual(cm.exception.code, "invalid")
        self.assertIn("Indtast et heltal", str(cm.exception.message))
