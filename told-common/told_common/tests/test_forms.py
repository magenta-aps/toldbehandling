from django.test import TestCase
from told_common.forms import TF10Form


class TF10FormTest(TestCase):
    def test_klasse_fjern_required(self):
        form = TF10Form(data={"kladde": True, "some_field": "abc"})
        form.is_valid()  # bind form and populate field data
        form.klasse_fjern_required()

        for _, field in form.fields.items():
            self.assertFalse(field.required)
