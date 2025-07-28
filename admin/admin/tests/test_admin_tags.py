# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from django.template import Context, Template
from django.test import RequestFactory, TestCase
from django.utils.translation import activate
from told_common.data import Vareafgiftssats

from admin.templatetags import admin_tags  # Replace with actual module


class TemplateTagsTest(TestCase):
    def setUp(self):
        activate("da")  # or "en", depending on your translation files

    def test_enhedsnavn_filter(self):
        self.assertEqual(
            admin_tags.enhedsnavn(Vareafgiftssats.Enhed.KILOGRAM), "kilogram"
        )
        self.assertEqual(admin_tags.enhedsnavn(Vareafgiftssats.Enhed.LITER), "liter")
        self.assertEqual(admin_tags.enhedsnavn(Vareafgiftssats.Enhed.ANTAL), "antal")
        self.assertEqual(
            admin_tags.enhedsnavn(Vareafgiftssats.Enhed.PROCENT), "procent"
        )
        self.assertEqual(
            admin_tags.enhedsnavn(Vareafgiftssats.Enhed.SAMMENSAT), "sammensat"
        )

    def test_nonced_tag_with_nonce(self):
        template_string = """
            {% load admin_tags %}
            {% nonced %}
            <script src="test.js"></script>
            {% endnonced %}
        """
        request = RequestFactory().get("/")
        request.csp_nonce = "abc123"
        context = Context({"request": request})

        rendered = Template(template_string).render(context)

        self.assertIn('nonce="abc123"', rendered)
        self.assertIn('<script nonce="abc123" src="test.js"></script>', rendered)

    def test_nonced_tag_without_nonce(self):
        template_string = """
            {% load admin_tags %}
            {% nonced %}
            <script src="test.js"></script>
            {% endnonced %}
        """
        request = RequestFactory().get("/")
        context = Context({"request": request})

        rendered = Template(template_string).render(context)

        self.assertNotIn("nonce=", rendered)
        self.assertIn('<script src="test.js"></script>', rendered)
