from common.models import EboksBesked
from django.test import TestCase


class CommonModelsTests(TestCase):
    def test_eboks_besked_content(self):
        db_model = EboksBesked()
        self.assertEqual(db_model.content, None)

        db_model = EboksBesked(
            titel="Test",
            cvr=1234567890,
            pdf=b"test-pdf-body",
        )
        self.assertEqual(
            db_model.content,
            (
                b"<?xml version='1.0' encoding='UTF-8'?>\n<Dispatch xmlns=\"urn:eboks:"
                b'en:3.0.0"><DispatchRecipient><Id>1234567890</Id><Type>V</Type><Nati'
                b"onality>DK</Nationality></DispatchRecipient><ContentTypeId></Content"
                b"TypeId><Title>Test</Title><Content><Data>dGVzdC1wZGYtYm9keQ==</Data>"
                b"<FileExtension>pdf</FileExtension></Content></Dispatch>"
            ),
        )

        db_model = EboksBesked(
            titel="Test",
            cpr=1122334455,
            pdf=b"test-pdf-body",
        )

        self.assertEqual(
            db_model.content,
            (
                b"<?xml version='1.0' encoding='UTF-8'?>\n<Dispatch xmlns=\"urn:eboks:en:3"
                b'.0.0"><DispatchRecipient><Id>1122334455</Id><Type>P</Type><Nationality>'
                b"DK</Nationality></DispatchRecipient><ContentTypeId></ContentTypeId><Titl"
                b"e>Test</Title><Content><Data>dGVzdC1wZGYtYm9keQ==</Data><FileExtension>p"
                b"df</FileExtension></Content></Dispatch>"
            ),
        )
