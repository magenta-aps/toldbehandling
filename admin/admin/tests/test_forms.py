# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0


from django.core.exceptions import ValidationError
from django.test import TestCase

from admin.forms import TF10ViewForm


class DummyToldkategori:
    def __init__(self, kategori, navn):
        self.kategori = kategori
        self.navn = navn


class TF10ViewFormTests(TestCase):
    def setUp(self):
        self.toldkategorier = [
            DummyToldkategori("01", "Madvarer"),
            DummyToldkategori("02", "Elektronik"),
        ]

    def test_clean_with_send_til_prisme_missing_fields(self):
        form = TF10ViewForm(
            self.toldkategorier,
            data={
                "send_til_prisme": True,
                # Missing toldkategori and modtager_stedkode
            },
        )
        self.assertFalse(form.is_valid())
        self.assertIn("toldkategori", form.errors)
        self.assertIn("modtager_stedkode", form.errors)

    def test_clean_with_send_til_prisme_all_fields_present(self):
        form = TF10ViewForm(
            self.toldkategorier,
            data={
                "send_til_prisme": True,
                "toldkategori": "01",
                "modtager_stedkode": "123",
            },
        )
        self.assertTrue(form.is_valid())

    def test_clean_without_send_til_prisme(self):
        form = TF10ViewForm(
            self.toldkategorier,
            data={
                "send_til_prisme": False,
                # Optional fields missing, but that’s OK
            },
        )
        self.assertTrue(form.is_valid())
