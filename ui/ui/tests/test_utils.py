import base64
import tempfile
from datetime import date
from io import BytesIO

from django.core.files.base import ContentFile
from django.http import QueryDict
from django.template import engines
from django.test import TestCase, override_settings
from django.utils.translation import get_language
from pypdf import PdfReader, PdfWriter
from told_common.util import (  # Adjust import path to your actual utils module
    format_daterange,
    get_file_base64,
    join,
    language,
    multivaluedict_to_querydict,
    opt_str,
    render_pdf,
    strtobool,
    write_pdf,
)


class GetFileBase64Test(TestCase):
    def test_get_file_base64(self):
        content = b"hello world"
        file = ContentFile(content, name="test.txt")
        result = get_file_base64(file)
        self.assertEqual(result, base64.b64encode(content).decode("utf-8"))


class StrToBoolTest(TestCase):
    def test_truthy_values(self):
        for val in ["yes", "true", "1", "on", "y", "t"]:
            self.assertEqual(strtobool(val), 1)

    def test_falsey_values(self):
        for val in ["no", "false", "0", "off", "n", "f"]:
            self.assertEqual(strtobool(val), 0)

    def test_invalid_value(self):
        with self.assertRaises(ValueError):
            strtobool("maybe")


class JoinTest(TestCase):
    def test_join(self):
        self.assertEqual(join(";", ["foo", "bar"]), "foo;bar")


class LanguageContextTest(TestCase):
    def test_language_switching(self):
        original_lang = get_language()
        self.assertEqual(original_lang, "da")
        with language("kl"):
            self.assertEqual(get_language(), "kl")
        self.assertEqual(get_language(), original_lang)


class OptStrTest(TestCase):
    def test_opt_str(self):
        self.assertIsNone(opt_str(None))
        self.assertEqual(opt_str(42), "42")
        self.assertEqual(opt_str("abc"), "abc")


class FormatDateRangeTest(TestCase):
    def test_full_range(self):
        result = format_daterange(date(2020, 1, 1), date(2020, 12, 31))
        self.assertEqual(result, "2020-01-01 - 2020-12-31")

    def test_open_start(self):
        result = format_daterange(None, date(2020, 12, 31))
        self.assertEqual(result, "al fortid - 2020-12-31")

    def test_open_end(self):
        result = format_daterange(date(2020, 1, 1), None)
        self.assertEqual(result, "2020-01-01 - al fremtid")

    def test_both_none(self):
        result = format_daterange(None, None)
        self.assertEqual(result, "altid")


class WritePdfTest(TestCase):
    def test_write_pdf_combines_pages(self):
        input_pdf = BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.write(input_pdf)
        input_pdf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_out:
            write_pdf(tmp_out.name, input_pdf)

        with open(tmp_out.name, "rb") as f:
            reader = PdfReader(f)
            self.assertEqual(len(reader.pages), 1)


class MultiValueDictToQueryDictTest(TestCase):
    def test_with_valid_data(self):
        data = {"foo": ["a", "b"], "bar": ["1"]}
        qd = multivaluedict_to_querydict(data)
        self.assertIsInstance(qd, QueryDict)
        self.assertEqual(qd.getlist("foo"), ["a", "b"])
        self.assertEqual(qd.getlist("bar"), ["1"])

    def test_with_empty_dict(self):
        qd = multivaluedict_to_querydict({})
        self.assertIsInstance(qd, QueryDict)
        self.assertEqual(qd.keys(), set())

    def test_with_none(self):
        qd = multivaluedict_to_querydict(None)
        self.assertIsInstance(qd, QueryDict)
        self.assertEqual(len(qd), 0)


class RenderPdfTest(TestCase):
    def setUp(self):
        # Add a simple in-memory template to the test environment
        self.engine = engines["django"]
        self.engine.engine.string_if_invalid = ""

        self.template_name = "test_template.html"
        self.template_content = "<html><body>Hello {{ name }}</body></html>"
        self.context = {"name": "World"}

        # Temporarily override templates for the test
        self.override = override_settings(
            TEMPLATES=[
                {
                    "BACKEND": "django.template.backends.django.DjangoTemplates",
                    "DIRS": [],
                    "OPTIONS": {
                        "loaders": [
                            (
                                "django.template.loaders.locmem.Loader",
                                {self.template_name: self.template_content},
                            )
                        ],
                    },
                }
            ]
        )
        self.override.enable()

    def tearDown(self):
        self.override.disable()

    def test_render_pdf_basic(self):
        pdf_bytes = render_pdf(self.template_name, self.context)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_render_pdf_with_html_modifier(self):
        def modifier(html: str):
            return html.replace("World", "Modified")

        pdf_bytes = render_pdf(self.template_name, self.context, html_modifier=modifier)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_render_pdf_with_stylesheets(self):
        # Use a temporary file to simulate a stylesheet
        with tempfile.NamedTemporaryFile(
            suffix=".css", mode="w", delete=False
        ) as css_file:
            css_file.write("body { color: red; }")
            css_path = css_file.name

        pdf_bytes = render_pdf(self.template_name, self.context, stylesheets=[css_path])
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
