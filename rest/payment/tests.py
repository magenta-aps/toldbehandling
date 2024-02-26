import random
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

from anmeldelse.models import PrivatAfgiftsanmeldelse, Varelinje
from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.forms import model_to_dict
from django.test import TestCase
from django.urls import reverse
from payment.api import generate_payment_item_from_varelinje
from payment.models import Payment
from payment.provider_handlers import get_provider_handler
from payment.schemas import (
    ContactDetails,
    ProviderCompanyResponse,
    ProviderConsumerResponse,
    ProviderOrderDetailsResponse,
    ProviderPaymentDetailsResponse,
    ProviderPaymentPayload,
)
from payment.utils import convert_keys_to_camel_case
from project.test_mixins import RestMixin
from project.util import json_dump
from sats.models import Afgiftstabel, Vareafgiftssats


class PaymentTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a test user which can handle payments
        cls.user_permissions = [
            Permission.objects.get(codename="view_payment"),
            Permission.objects.get(codename="add_payment"),
            Permission.objects.get(codename="change_payment"),
            Permission.objects.get(codename="delete_payment"),
        ]

        cls.user, cls.user_token, cls.user_refresh_token = RestMixin.make_user(
            username="payment-test-user",
            plaintext_password="testpassword1337",
            permissions=cls.user_permissions,
        )
        cls.user.user_permissions.add(
            Permission.objects.get(codename="view_privatafgiftsanmeldelse"),
        )

        # Create a test declaration
        db_declaration_name = (
            random.choice(["Jens", "Peter", "Hans", "Søren", "Niels"])
            + " "
            + random.choice(["Jensen", "Petersen", "Hansen", "Sørensen", "Nielsen"])
        )

        cls.declaration = PrivatAfgiftsanmeldelse.objects.create(
            cpr=random.randint(1000000000, 9999999999),
            navn=db_declaration_name,
            adresse="Ligustervænget " + str(random.randint(1, 100)),
            by="TestBy",
            postnummer=1234,
            telefon=str(random.randint(100000, 999999)),
            bookingnummer=str(random.randint(100000, 999999)),
            leverandørfaktura_nummer=str(random.randint(100000, 999999)),
            indførselstilladelse=None,
            indleveringsdato=date.today() + timedelta(days=random.randint(10, 30)),
            status=random.choice(["ny", "afvist", "godkendt"]),
            oprettet_af=cls.user,
        )

        # Create a test afgiftstabel
        cls.afgiftstabel = Afgiftstabel.objects.create(
            gyldig_fra=datetime.now(timezone.utc).isoformat()
        )

        # Create a test vareafgiftssats
        cls.vareafgiftssats_personbiler = Vareafgiftssats.objects.create(
            afgiftstabel=cls.afgiftstabel,
            afgiftsgruppenummer=72,
            vareart_da="PERSONBILER Afgiften test",
            vareart_kl="PERSONBILER Afgiften test",
            enhed=Vareafgiftssats.Enhed.SAMMENSAT,
            minimumsbeløb=None,
            afgiftssats=Decimal("137.00"),
            kræver_indførselstilladelse=False,
        )

        # Create declaraton items
        cls.declaration_items = [
            Varelinje.objects.create(
                privatafgiftsanmeldelse=cls.declaration,
                vareafgiftssats=cls.vareafgiftssats_personbiler,
                mængde=1,
                antal=1,
                fakturabeløb=1337,
                afgiftsbeløb=668,
            )
        ]


class NetsPaymentProviderTests(TestCase):
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

    @patch("payment.provider_handlers.requests.get")
    def test_nets_read(self, mock_requests_get):
        test_provider_payment_id = str(uuid.uuid4()).replace("-", "").lower()

        # Configure mock(s)
        mock_requests_get.return_value.status_code = 200
        mock_requests_get.return_value.json.return_value = {
            "payment": {
                "paymentId": test_provider_payment_id,
            }
        }

        resp = self.handler.read(payment_id=test_provider_payment_id)
        self.assertNotEqual(resp, None)

        mock_requests_get.assert_called_once_with(
            f"{self.handler.host}/v1/payments/{test_provider_payment_id}",
            headers=self.handler.headers,
        )

    def test_nets_charge(self):
        # TDODO: make this test when the MR with the new 'charge' method is merged
        pass


class PaymentAPITests(PaymentTest):
    @patch("payment.api.get_provider_handler")
    def test_create_nets(self, mock_get_provider_handler):
        provider_name = "nets"
        fake_nets_payment = {
            "paymentId": "1234",
            "paymentDetails": ProviderPaymentDetailsResponse(
                invoice_details={},
                card_details={},
            ),
            "orderDetails": ProviderOrderDetailsResponse(
                amount=1337,
                currency="DKK",
                reference="1234",
            ),
            "consumer": ProviderConsumerResponse(
                shippingAddress={},
                company=ProviderCompanyResponse(
                    contact_details=ContactDetails(
                        phone_number={},
                    )
                ),
                privatePerson=ContactDetails(
                    phone_number={},
                ),
                billingAddress={},
            ),
            "checkout": {},
            "created": datetime.now(timezone.utc).isoformat(),
        }

        mock_nets_provider = MagicMock(
            initial_status="created",
            host=settings.PAYMENT_PROVIDER_NETS_HOST,
            terms_url=settings.PAYMENT_PROVIDER_NETS_TERMS_URL,
            create=MagicMock(return_value=fake_nets_payment),
            read=MagicMock(return_value=fake_nets_payment),
        )

        mock_get_provider_handler.return_value = mock_nets_provider

        # Invoke the API endpoint
        resp = self.client.post(
            reverse("api-1.0.0:payment_create"),
            data=json_dump(
                {
                    "declaration_id": self.declaration.id,
                    "provider": provider_name,
                }
            ),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 201)

        mock_get_provider_handler.assert_called_once_with(provider_name)
        mock_nets_provider.create.assert_called_once_with(
            ProviderPaymentPayload(
                declaration_id=self.declaration.id,
                amount=38700,  # FYI: (137*100) + (250*100)
                currency="DKK",
                reference=self.declaration.id,
                provider=provider_name,
                items=[
                    generate_payment_item_from_varelinje(self.declaration_items[0]),
                    {
                        "reference": "tillægsafgift",
                        "name": "Tillægsafgift",
                        "quantity": 1.0,
                        "unit": "ant",
                        "unit_price": 0,
                        "tax_rate": 0,
                        "tax_amount": 0,
                        "gross_total_amount": 0,
                        "net_total_amount": 0,
                    },
                    {
                        "reference": "ekspeditionsgebyr",
                        "name": "Ekspeditionsgebyr",
                        "quantity": 1.0,
                        "unit": "ant",
                        "unit_price": 25000,
                        "tax_rate": 0,
                        "tax_amount": 0,
                        "gross_total_amount": 25000,
                        "net_total_amount": 25000,
                    },
                ],
            ),
            f"{settings.HOST_DOMAIN}/payment/checkout/{self.declaration.id}",
        )

    def test_list(self):
        pass

    def test_get(self):
        pass

    def test_refresh(self):
        pass
