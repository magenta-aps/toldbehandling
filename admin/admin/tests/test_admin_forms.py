# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytz
from django.test import TestCase, override_settings
from django.utils.timezone import get_default_timezone
from django.utils.translation import activate

from admin.forms import AfgiftstabelUpdateForm


class AfgiftstabelUpdateFormTest(TestCase):
    def setUp(self):
        activate("da")  # Ensures Danish translations are loaded if needed

    def test_missing_gyldig_fra_adds_error(self):
        form = AfgiftstabelUpdateForm(
            data={
                "kladde": "True",
                "delete": False,  # Not marked for deletion
                # "gyldig_fra" is omitted on purpose
                "offset": 120,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("gyldig_fra", form.errors)
        self.assertEqual(
            form.errors["gyldig_fra"],
            [form.fields["gyldig_fra"].error_messages["required"]],
        )

    def test_gyldig_fra_with_empty_offset_uses_default_timezone(self):
        # Create a valid future datetime string matching the input format
        naive_dt = datetime.now() + timedelta(days=1)
        formatted_dt = naive_dt.strftime("%d/%m/%Y %H:%M")

        form = AfgiftstabelUpdateForm(
            data={
                "gyldig_fra": formatted_dt,
                "kladde": "True",
                "offset": "",  # Trigger the offset=None branch
                "delete": False,
            }
        )

        self.assertTrue(form.is_valid(), msg=form.errors)
        cleaned = form.cleaned_data
        gyldig_fra = cleaned["gyldig_fra"]

        self.assertIsNotNone(gyldig_fra.tzinfo)
        self.assertEqual(gyldig_fra.tzinfo, get_default_timezone())

    def test_gyldig_fra_in_past_raises_validation_error(self):
        past_dt = datetime.now(timezone.utc) - timedelta(days=1)
        formatted_past_dt = past_dt.strftime("%d/%m/%Y %H:%M")

        form = AfgiftstabelUpdateForm(
            data={
                "gyldig_fra": formatted_past_dt,
                "kladde": "True",
                "offset": 120,
                "delete": False,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("gyldig_fra", form.errors)
        self.assertIn("Dato skal være efter i dag", form.errors["gyldig_fra"][0])
