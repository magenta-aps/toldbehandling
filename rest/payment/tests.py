import random
import uuid
from datetime import date, timedelta
from unittest import mock
from unittest.mock import patch

from anmeldelse.models import PrivatAfgiftsanmeldelse
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from payment.api import provider_payment_validation
from payment.models import Payment
from payment.provider_handlers import get_provider_handler
from payment.schemas import ProviderPaymentPayload
from payment.utils import convert_keys_to_camel_case


class PaymentProviderTest(TestCase):
    def setUp(self):
        self.handler = get_provider_handler(settings.PAYMENT_PROVIDER_NETS)

    @classmethod
    def setUpTestData(cls):
        user = User.objects.create(
            username="payment-test-user",
            email="payment-test-user@magenta-aps.dk",
        )

        db_declaration_name = (
            random.choice(["Jens", "Peter", "Hans", "Søren", "Niels"])
            + " "
            + random.choice(["Jensen", "Petersen", "Hansen", "Sørensen", "Nielsen"])
        )
        db_declaration_addr = "Ligustervænget " + str(random.randint(1, 100))
        PrivatAfgiftsanmeldelse.objects.create(
            cpr=random.randint(1000000000, 9999999999),
            navn=db_declaration_name,
            adresse=db_declaration_addr,
            by="TestBy",
            postnummer=1234,
            telefon=str(random.randint(100000, 999999)),
            bookingnummer=str(random.randint(100000, 999999)),
            leverandørfaktura_nummer=str(random.randint(100000, 999999)),
            indførselstilladelse=None,
            indleveringsdato=date.today() + timedelta(days=random.randint(10, 30)),
            status=random.choice(["ny", "afvist", "godkendt"]),
            oprettet_af=user,
        )

    @patch("payment.provider_handlers.NetsProviderHandler.read")
    @patch("payment.provider_handlers.requests.post")
    def test_nets_create(self, mock_requests_post, mock_handler_read):
        # Configure test-data for this test
        user = User.objects.get(username="payment-test-user")
        self.assertNotEqual(user, None)

        db_declaration = PrivatAfgiftsanmeldelse.objects.filter(
            oprettet_af=user
        ).first()
        self.assertNotEqual(db_declaration, None)

        db_payment = Payment.objects.create(
            status="created",
            amount=1337,
            currency="DKK",
            reference=db_declaration.id,
            declaration=db_declaration,
            provider_payment_id=str(uuid.uuid4()).replace("-", "").lower(),
        )

        checkout_url = "https://example.com/checkout"

        # Configure mock(s)
        mock_requests_post.return_value.status_code = 201
        mock_requests_post.return_value.json.return_value = {
            "paymentId": db_payment.provider_payment_id,
            "checkout": {
                "url": checkout_url,
            },
        }

        # Create the payment
        db_model = ProviderPaymentPayload(
            declaration_id=db_declaration.id,
            amount=1337,
            currency="DKK",
            reference="1234",
            provider=settings.PAYMENT_PROVIDER_NETS,
            items=[
                {
                    "reference": "1234",
                    "name": "Kaffe",
                    "quantity": 1,
                    "unit": "KG",
                    "unit_price": 1337,
                    "tax_rate": 0,
                    "tax_amount": 0,
                    "gross_total_amount": 1337,
                    "net_total_amount": 1337,
                }
            ],
        )

        # Invoke the function we want to test
        resp = self.handler.create(
            db_model,
            checkout_url,
        )

        mock_requests_post.assert_called_once_with(
            f"{self.handler.host}/v1/payments",
            headers=self.handler.headers,
            json={
                "order": convert_keys_to_camel_case(db_model.dict()),
                "checkout": {
                    "url": checkout_url,
                    "termsUrl": self.handler.terms_url,
                },
            },
        )

        mock_handler_read.assert_called_once_with(db_payment.provider_payment_id)

    def test_nets_read(self):
        pass

    def test_nets_charge(self):
        pass
