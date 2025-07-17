from unittest.mock import MagicMock

from django.test import TestCase

from admin.forms import TF10ViewForm


class FormsTest(TestCase):
    def test_tf10_view_clean_toldkategori_none(self):
        test_kategorier = [
            MagicMock(kategori="M1337", navn="Test kategori"),
            MagicMock(kategori="M1338", navn="Test kategori2"),
        ]

        form = TF10ViewForm(
            toldkategorier=test_kategorier,
            data={
                "status": "ny",
                "send_til_prisme": True,
                "toldkategori": None,
            },
        )

        # Asserts
        self.assertFalse(form.is_valid())
        self.assertIn("toldkategori", form.errors)
