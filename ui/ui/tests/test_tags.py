from urllib.parse import unquote as std_unquote

from django.core.files.base import ContentFile
from django.test import SimpleTestCase
from told_common.templatetags.common_tags import (
    divide,
    file_basename,
    get,
    strip,
    unquote,
    zfill,
)


class TemplateFiltersTest(SimpleTestCase):
    def test_file_basename_with_string_path(self):
        path = "/some/path/to/file.txt"
        self.assertEqual(file_basename(path), "file.txt")

    def test_file_basename_with_file_instance(self):
        f = ContentFile(b"data", name="folder/file.pdf")
        self.assertEqual(file_basename(f), "file.pdf")

    def test_file_basename_with_url_encoded_name(self):
        encoded_path = "/path/to/some%20file.txt"
        self.assertEqual(file_basename(encoded_path), std_unquote("some%20file.txt"))

    def test_file_basename_with_none(self):
        self.assertEqual(file_basename(None), "")

    def test_zfill_with_string_and_int(self):
        self.assertEqual(zfill("7", 3), "007")
        self.assertEqual(zfill(42, 5), "00042")

    def test_unquote_decodes_string(self):
        encoded = "hello%20world%21"
        self.assertEqual(unquote(encoded), "hello world!")

    def test_get_with_object_attribute(self):
        class Dummy:
            foo = "bar"

        d = Dummy()
        self.assertEqual(get(d, "foo"), "bar")

    def test_get_with_dict_key(self):
        d = {"key": "value"}
        self.assertEqual(get(d, "key"), "value")

    def test_get_with_dict_key_int_cast(self):
        d = {"1": "one"}
        self.assertEqual(get(d, 1), "one")

    def test_get_with_list_index(self):
        self.assertEqual(get(["zero", "one", "two"], 1), "one")

    def test_get_with_tuple_index(self):
        t = ("a", "b", "c")
        self.assertEqual(get(t, 2), "c")

    def test_get_with_get_method(self):
        class DummyDictLike:
            def get(self, key):
                if key == "exists":
                    return "found"
                return None

        d = DummyDictLike()
        self.assertEqual(get(d, "exists"), "found")
        self.assertIsNone(get(d, "missing"))

    def test_get_with_missing_attribute_and_key(self):
        d = {"a": 1}
        self.assertIsNone(get(d, "missing"))
        self.assertIsNone(get(None, "anything"))

    def test_divide_with_valid_values(self):
        self.assertEqual(divide(10, 2), 5)

    def test_divide_with_string_values(self):
        self.assertEqual(divide("9", "3"), 3)

    def test_divide_by_zero_returns_none(self):
        self.assertIsNone(divide(10, 0))

    def test_divide_with_invalid_values_returns_none(self):
        self.assertIsNone(divide("foo", "bar"))

    def test_strip_removes_whitespace(self):
        self.assertEqual(strip("  hello "), "hello")

    def test_strip_with_empty_string(self):
        self.assertEqual(strip(""), "")

    def test_strip_with_only_whitespace(self):
        self.assertEqual(strip("   "), "")
