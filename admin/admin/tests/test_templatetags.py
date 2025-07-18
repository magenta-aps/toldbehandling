from django.test import SimpleTestCase
from django.utils.translation import activate, deactivate
from told_common.data import Vareafgiftssats

from admin.templatetags.admin_tags import enhedsnavn


class EnhedsnavnFilterTest(SimpleTestCase):
    def setUp(self):
        activate("da")

    def tearDown(self):
        deactivate()

    def test_enhedsnavn_kilogram(self):
        self.assertEqual(str(enhedsnavn(Vareafgiftssats.Enhed.KILOGRAM)), "kilogram")

    def test_enhedsnavn_liter(self):
        self.assertEqual(str(enhedsnavn(Vareafgiftssats.Enhed.LITER)), "liter")

    def test_enhedsnavn_antal(self):
        self.assertEqual(str(enhedsnavn(Vareafgiftssats.Enhed.ANTAL)), "antal")

    def test_enhedsnavn_procent(self):
        self.assertEqual(str(enhedsnavn(Vareafgiftssats.Enhed.PROCENT)), "procent")

    def test_enhedsnavn_sammensat(self):
        self.assertEqual(str(enhedsnavn(Vareafgiftssats.Enhed.SAMMENSAT)), "sammensat")
