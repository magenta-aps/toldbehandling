from django.test import TestCase
from told_common.templatetags.common_tags import file_basename, zfill


class TemplateTagsTest(TestCase):
    def test_file_basename(self):
        self.assertEquals(file_basename("/path/to/file.txt"), "file.txt")

    def test_zfill(self):
        self.assertEquals(zfill("444", 10), "0000000444")
