from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.utils.timezone import is_aware

from admin.forms import AfgiftstabelUpdateForm, TF10ViewForm


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

    def test_afgiftstabel_update_form_clean_invalid_gyldig_fra(self):
        form = AfgiftstabelUpdateForm(
            data={
                "delete": False,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("gyldig_fra", form.errors)

    def test_afgiftstabel_update_form_clean(self):
        gyldig_fra = datetime.now(timezone.utc) + timedelta(days=1)
        form = AfgiftstabelUpdateForm(data={"gyldig_fra": gyldig_fra})

        self.assertTrue(form.is_valid())
        self.assertEqual(gyldig_fra.tzinfo, timezone.utc)
        self.assertEqual(
            form.cleaned_data["gyldig_fra"].tzinfo, ZoneInfo("America/Nuuk")
        )

    def test_afgiftstabel_update_form_clean_gyldig_fra_error(self):
        gyldig_fra = datetime.now(timezone.utc)
        form = AfgiftstabelUpdateForm(data={"gyldig_fra": gyldig_fra})
        self.assertFalse(form.is_valid())
        self.assertIn("gyldig_fra", form.errors)
        self.assertEqual(
            form.errors["gyldig_fra"],
            ["Dato skal være efter i dag", "Dette felt er påkrævet."],
        )
