# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from unittest import TestCase

from django.core.exceptions import ValidationError
from project.util import json_dump, save_or_raise_409, strtobool


class UtilTest(TestCase):
    def test_json_dump(self):
        class NonSerializable:
            pass

        with self.assertRaises(TypeError):
            json_dump({"foo": NonSerializable()})

        self.assertEqual(
            json_dump(ValidationError(["error1", "error2"])), b'["error1","error2"]'
        )
        self.assertEqual(
            json_dump(ValidationError({"field": "hephey"})), b'{"field":["hephey"]}'
        )

    def test_strtobool(self):
        for true_value in ("y", "yes", "t", "true", "on", "1"):
            for value in (true_value.lower(), true_value.upper()):
                self.assertEqual(strtobool(value), 1)
        for true_value in ("n", "no", "f", "false", "off", "0"):
            for value in (true_value.lower(), true_value.upper()):
                self.assertEqual(strtobool(value), 0)
        for value in ("j", "ja", "nej", "null", "None", "yep", "hephey", "2"):
            with self.assertRaises(ValueError):
                strtobool(value)

    class DummyItem:
        def save(self):
            # Raise a non-concurrency ValidationError
            raise ValidationError("Some validation error", code="some_error")

    def test_non_concurrency_validation_error_is_reraised(self):
        item = self.DummyItem()

        with self.assertRaises(ValidationError) as cm:
            save_or_raise_409(item)

        exc = cm.exception
        # Check that the exception is the original one
        self.assertEqual(exc.message, "Some validation error")
        self.assertEqual(exc.code, "some_error")
