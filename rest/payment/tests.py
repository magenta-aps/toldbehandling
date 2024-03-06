import random
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, call, patch

from anmeldelse.models import PrivatAfgiftsanmeldelse, Varelinje
from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from payment.api import generate_payment_item_from_varelinje
from payment.exceptions import (
    ProviderHandlerNotFound,
    ProviderPaymentCreateError,
    ProviderPaymentNotFound,
)
from payment.models import Payment
from payment.provider_handlers import get_provider_handler
from payment.schemas import (
    ContactDetails,
    ProviderCompanyResponse,
    ProviderConsumerResponse,
    ProviderOrderDetailsResponse,
    ProviderPaymentCheckoutResponse,
    ProviderPaymentDetailsResponse,
    ProviderPaymentPayload,
    ProviderPaymentResponse,
    ProviderPaymentSummaryResponse,
)
from payment.utils import (
    convert_keys_to_camel_case,
    generate_payment_item_from_varelinje,
)
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

        # Create test declarations
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

        db_declaration_2_name = (
            random.choice(["Jens", "Peter", "Hans", "Søren", "Niels"])
            + " "
            + random.choice(["Jensen", "Petersen", "Hansen", "Sørensen", "Nielsen"])
        )

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

        cls.declaration_2 = PrivatAfgiftsanmeldelse.objects.create(
            cpr=random.randint(1000000000, 9999999999),
            navn=db_declaration_2_name,
            adresse="Ligustervænget " + str(random.randint(1, 100)),
            by="TestBy",
            postnummer=4321,
            telefon=str(random.randint(100000, 999999)),
            bookingnummer=str(random.randint(100000, 999999)),
            leverandørfaktura_nummer=str(random.randint(100000, 999999)),
            indførselstilladelse=None,
            indleveringsdato=date.today() + timedelta(days=random.randint(10, 30)),
            status=random.choice(["ny", "afvist", "godkendt"]),
            oprettet_af=cls.user,
        )

        cls.declaration_2_items = [
            Varelinje.objects.create(
                privatafgiftsanmeldelse=cls.declaration_2,
                vareafgiftssats=cls.vareafgiftssats_personbiler,
                mængde=1,
                antal=1,
                fakturabeløb=7331,
                afgiftsbeløb=866,
            ),
            Varelinje.objects.create(
                privatafgiftsanmeldelse=cls.declaration_2,
                vareafgiftssats=cls.vareafgiftssats_personbiler,
                mængde=1,
                antal=1,
                fakturabeløb=0,
                afgiftsbeløb=0,
            ),
        ]

    @classmethod
    def provider_handler_read_mock(cls, payment_id: str, data: dict):
        return data.get(payment_id)

    def _create_test_payment(
        self,
        status: str,
        amount: int,
        declaration: PrivatAfgiftsanmeldelse,
        provider_payment_id: str,
        currency: str = "DKK",
    ) -> Payment:
        return Payment.objects.create(
            status=status,
            amount=amount,
            currency=currency,
            reference=declaration.id,
            declaration=declaration,
            provider_payment_id=provider_payment_id,
        )

    def _create_test_payment_with_fake_provider_payment(
        self,
        status: str,
        amount: int,
        declaration: PrivatAfgiftsanmeldelse,
        provider_payment_id: str,
        provider_payment_summary: ProviderPaymentSummaryResponse | None = None,
        currency: str = "DKK",
    ) -> tuple[Payment, ProviderPaymentResponse]:
        test_payment = self._create_test_payment(
            status=status,
            amount=amount,
            declaration=declaration,
            provider_payment_id=provider_payment_id,
            currency=currency,
        )

        fake_provider_payment = ProviderPaymentResponse(
            payment_id=provider_payment_id,
            summary=(
                ProviderPaymentSummaryResponse(
                    reserved_amount=0,
                    charged_amount=0,
                    refunded_amount=0,
                    cancelled_amount=0,
                )
                if provider_payment_summary is None
                else provider_payment_summary
            ),
            consumer=ProviderConsumerResponse(
                shipping_address={},
                company=ProviderCompanyResponse(
                    contact_details=ContactDetails(
                        phone_number={},
                    )
                ),
                private_person=ContactDetails(
                    phone_number={},
                ),
                billing_address={},
            ),
            payment_details=ProviderPaymentDetailsResponse(
                invoice_details={},
                card_details={},
            ),
            order_details=ProviderOrderDetailsResponse(
                amount=amount,
                currency=currency,
                reference=declaration.id,
            ),
            checkout=ProviderPaymentCheckoutResponse(
                url=f"{settings.HOST_DOMAIN}/payment/checkout/{declaration.id}",
                cancel_url=f"{settings.HOST_DOMAIN}/payment/cancel/{declaration.id}",
            ),
            created=datetime.now(timezone.utc).isoformat(),
        )

        return test_payment, fake_provider_payment


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
        cls.declaration = PrivatAfgiftsanmeldelse.objects.create(
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
        create_payload = ProviderPaymentPayload(
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
            create_payload,
            checkout_url,
        )

        mock_requests_post.assert_called_once_with(
            f"{self.handler.host}/v1/payments",
            headers=self.handler.headers,
            json={
                "order": convert_keys_to_camel_case(create_payload.dict()),
                "checkout": {
                    "url": checkout_url,
                    "termsUrl": self.handler.terms_url,
                },
            },
        )

        mock_handler_read.assert_called_once_with(db_payment.provider_payment_id)

    @patch("payment.provider_handlers.requests.post")
    def test_nets_create_error(self, mock_requests_post):
        test_create_payload = ProviderPaymentPayload(
            declaration_id=self.declaration.id,
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
        test_checkout_url = "https://example.com/checkout"

        mock_requests_post.return_value.status_code = 500

        expected_exception: ProviderPaymentCreateError | None = None
        try:
            resp = self.handler.create(
                test_create_payload,
                test_checkout_url,
            )
        except ProviderPaymentCreateError as e:
            expected_exception = e

        self.assertNotEqual(expected_exception, None)
        self.assertEqual(
            expected_exception.detail,
            ProviderPaymentCreateError.default_detail.format(
                response_text=mock_requests_post.return_value.text,
                endpoint=f"{self.handler.host}/v1/payments",
                endpoint_status=mock_requests_post.return_value.status_code,
            ),
        )

    @patch("payment.provider_handlers.requests.get")
    def test_nets_read(self, mock_requests_get):
        test_provider_payment_id = str(uuid.uuid4()).replace("-", "").lower()
        test_provider_payment = {
            "payment_id": test_provider_payment_id,
            "summary": {
                "reserved_amount": 0,
                "charged_amount": 0,
                "refunded_amount": 0,
                "cancelled_amount": 0,
            },
            "consumer": {
                "shipping_address": {},
                "company": {"contact_details": {"phone_number": {}}},
                "private_person": {"phone_number": {}},
                "billing_address": {},
            },
            "payment_details": {
                "payment_type": None,
                "payment_method": None,
                "invoice_details": {},
                "card_details": {},
            },
            "order_details": {
                "amount": 1337,
                "currency": "DKK",
                "reference": "1234",
            },
            "checkout": {
                "url": f"{settings.HOST_DOMAIN}/payment/checkout/{self.declaration.id}",
                "cancel_url": f"{settings.HOST_DOMAIN}/payment/cancel/{self.declaration.id}",
            },
            "created": datetime.now(timezone.utc).isoformat(),
        }

        # Configure mock(s)
        mock_requests_get.return_value.status_code = 200
        mock_requests_get.return_value.json.return_value = {
            "payment": {**test_provider_payment}
        }

        resp = self.handler.read(payment_id=test_provider_payment_id)
        self.assertEqual(resp.dict(), test_provider_payment)

        mock_requests_get.assert_called_once_with(
            f"{self.handler.host}/v1/payments/{test_provider_payment_id}",
            headers=self.handler.headers,
        )

    @patch("payment.provider_handlers.requests.get")
    def test_nets_read_not_found(self, mock_requests_get):
        test_provider_payment_id = str(uuid.uuid4()).replace("-", "").lower()
        mock_requests_get.return_value.status_code = 500

        expected_exception: ProviderPaymentNotFound | None = None
        try:
            _ = self.handler.read(payment_id=test_provider_payment_id)
        except ProviderPaymentNotFound as e:
            expected_exception = e

        self.assertNotEqual(expected_exception, None)
        self.assertEqual(
            expected_exception.detail,
            ProviderPaymentNotFound.default_detail.format(
                payment_id=test_provider_payment_id,
                endpoint=f"{self.handler.host}/v1/payments/{test_provider_payment_id}",
                endpoint_status=mock_requests_get.return_value.status_code,
            ),
        )

    @patch("payment.provider_handlers.requests.post")
    def test_nets_charge(self, mock_requests_post):
        payment_id = str(uuid.uuid4()).replace("-", "").lower()
        charge_amount = 1337

        mock_requests_post.return_value.status_code = 201

        resp = self.handler.charge(
            payment_id=payment_id,
            amount=charge_amount,
        )

        mock_requests_post.assert_called_once_with(
            f"{settings.PAYMENT_PROVIDER_NETS_HOST}/v1/payments/{payment_id}/charges",
            headers={
                "content-type": "application/*+json",
                "Authorization": f"Bearer {settings.PAYMENT_PROVIDER_NETS_SECRET_KEY}",
            },
            json={
                "amount": charge_amount,
            },
        )


class PaymentAPITests(PaymentTest):
    @patch("payment.api.get_provider_handler")
    def test_create_nets(self, mock_get_provider_handler):
        provider_name = "nets"
        fake_nets_payment = ProviderPaymentResponse(
            payment_id="1234",
            summary=ProviderPaymentSummaryResponse(
                reserved_amount=0,
                charged_amount=0,
                refunded_amount=0,
                cancelled_amount=0,
            ),
            consumer=ProviderConsumerResponse(
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
            payment_details=ProviderPaymentDetailsResponse(
                invoice_details={},
                card_details={},
            ),
            order_details=ProviderOrderDetailsResponse(
                amount=1337,
                currency="DKK",
                reference="1234",
            ),
            checkout=ProviderPaymentCheckoutResponse(
                url=f"{settings.HOST_DOMAIN}/payment/checkout/{self.declaration.id}",
                cancel_url=f"{settings.HOST_DOMAIN}/payment/cancel/{self.declaration.id}",
            ),
            created=datetime.now(timezone.utc).isoformat(),
        )

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

    def test_create_declaration_not_found(self):
        resp = self.client.post(
            reverse("api-1.0.0:payment_create"),
            data=json_dump(
                {
                    "declaration_id": 99999,
                    "provider": "nets",
                }
            ),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 400)

    def test_create_invalid_provider(self):
        invalid_provider_handler = "invalid"
        resp = self.client.post(
            reverse("api-1.0.0:payment_create"),
            data=json_dump(
                {
                    "declaration_id": self.declaration.id,
                    "provider": invalid_provider_handler,
                }
            ),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

        resp_data = resp.json()
        self.assertEqual(
            resp_data,
            {
                "detail": ProviderHandlerNotFound.default_detail.format(
                    provider=invalid_provider_handler
                ),
            },
        )

    def test_create_bank_provider_missing_permission(self):
        resp = self.client.post(
            reverse("api-1.0.0:payment_create"),
            data=json_dump(
                {
                    "declaration_id": self.declaration.id,
                    "provider": "bank",
                }
            ),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 403)

    @patch("payment.api.get_provider_handler")
    def test_create_nets_existing_db_payment(self, mock_get_provider_handler):
        # Test data
        (
            test_payment,
            fake_provider_payment,
        ) = self._create_test_payment_with_fake_provider_payment(
            status="created",
            amount=1337,
            declaration=self.declaration,
            provider_payment_id="1234",
        )

        # Configure mock(s)
        mock_nets_provider = MagicMock(
            host=settings.PAYMENT_PROVIDER_NETS_HOST,
            initial_status="created",
            read=MagicMock(side_effect=lambda x: fake_provider_payment),
            create=MagicMock(side_effect=lambda *args: fake_provider_payment),
        )
        mock_get_provider_handler.return_value = mock_nets_provider

        # NOTE: It is intentional that Payment.create+save is patched
        # after test-datacreation
        with patch(
            "payment.models.Payment.objects.create"
        ) as mock_payment_model_create, patch(
            "payment.models.Payment.save"
        ) as mock_payment_model_save:
            mock_payment_model_create.return_value = test_payment

            # Invoke the API endpoint
            resp = self.client.post(
                reverse("api-1.0.0:payment_create"),
                data=json_dump(
                    {
                        "declaration_id": self.declaration.id,
                        "provider": "nets",
                    }
                ),
                HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
                content_type="application/json",
            )
            self.assertEqual(resp.status_code, 201)
            mock_payment_model_create.assert_not_called()
            mock_payment_model_save.assert_not_called()

    @patch("payment.api.get_provider_handler")
    def test_list_nets(self, mock_get_provider_handler):
        # Create test data
        (
            test_payment_1,
            fake_provider_payment_1,
        ) = self._create_test_payment_with_fake_provider_payment(
            status="created",
            amount=1337,
            declaration=self.declaration,
            provider_payment_id="1234",
        )

        (
            test_payment_2,
            fake_provider_payment_2,
        ) = self._create_test_payment_with_fake_provider_payment(
            status="created",
            amount=7331,
            declaration=self.declaration_2,
            provider_payment_id="5678",
        )

        fake_provider_payments = {
            fake_provider_payment_1.payment_id: fake_provider_payment_1,
            fake_provider_payment_2.payment_id: fake_provider_payment_2,
        }

        # Configure mock(s)
        mock_nets_provider = MagicMock(
            host=settings.PAYMENT_PROVIDER_NETS_HOST,
            initial_status="created",
            read=MagicMock(
                side_effect=lambda x: (
                    fake_provider_payments[x] if x in fake_provider_payments else None
                )
            ),
        )
        mock_get_provider_handler.return_value = mock_nets_provider

        # Invoke the API endpoint
        resp = self.client.get(
            reverse("api-1.0.0:payment_list"),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )

        self.assertEqual(resp.status_code, 200)
        mock_get_provider_handler.assert_called_once_with("nets")
        mock_nets_provider.read.assert_has_calls(
            [
                call(test_payment_1.provider_payment_id),
                call(test_payment_2.provider_payment_id),
            ]
        )

    @patch("payment.api.get_provider_handler")
    def test_list_specifiy_declaration_id(self, mock_get_provider_handler):
        # Create test data
        (
            test_payment_1,
            fake_provider_payment_1,
        ) = self._create_test_payment_with_fake_provider_payment(
            status="created",
            amount=1337,
            declaration=self.declaration,
            provider_payment_id="1234",
        )

        (
            test_payment_2,
            fake_provider_payment_2,
        ) = self._create_test_payment_with_fake_provider_payment(
            status="created",
            amount=7331,
            declaration=self.declaration_2,
            provider_payment_id="5678",
        )

        fake_provider_payments = {
            fake_provider_payment_1.payment_id: fake_provider_payment_1,
            fake_provider_payment_2.payment_id: fake_provider_payment_2,
        }

        # Configure mock(s)
        mock_nets_provider = MagicMock(
            host=settings.PAYMENT_PROVIDER_NETS_HOST,
            initial_status="created",
            read=MagicMock(
                side_effect=lambda x: (
                    fake_provider_payments[x] if x in fake_provider_payments else None
                )
            ),
        )
        mock_get_provider_handler.return_value = mock_nets_provider

        # Invoke the API endpoint
        resp = self.client.get(
            reverse("api-1.0.0:payment_list"),
            QUERY_STRING=f"declaration={self.declaration.id}",
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )

        # Assert everything happened as expected
        self.assertEqual(resp.status_code, 200)
        mock_get_provider_handler.assert_called_once_with("nets")
        mock_nets_provider.read.assert_called_once_with(
            test_payment_1.provider_payment_id
        )

    @patch("payment.api.get_provider_handler")
    def test_get_nets(self, mock_get_provider_handler):
        (
            test_payment,
            fake_provider_payment,
        ) = self._create_test_payment_with_fake_provider_payment(
            status="created",
            amount=1337,
            declaration=self.declaration,
            provider_payment_id="1234",
        )

        # Configure mock(s)
        mock_nets_provider = MagicMock(
            host=settings.PAYMENT_PROVIDER_NETS_HOST,
            initial_status="created",
            read=MagicMock(return_value=fake_provider_payment),
        )

        mock_get_provider_handler.return_value = mock_nets_provider

        # Invoke the API endpoint
        resp = self.client.get(
            reverse("api-1.0.0:payment_get", kwargs={"payment_id": test_payment.id}),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )

        self.assertEqual(resp.status_code, 200)
        mock_get_provider_handler.assert_called_once_with("nets")
        mock_nets_provider.read.assert_called_once_with(
            test_payment.provider_payment_id
        )

    @patch("payment.api.get_provider_handler")
    def test_refresh_nets(self, mock_get_provider_handler):
        # Test data
        (
            test_payment,
            fake_provider_payment,
        ) = self._create_test_payment_with_fake_provider_payment(
            status="created",
            amount=1337,
            declaration=self.declaration,
            provider_payment_id="1234",
        )

        # Configure mock(s)
        mock_nets_provider = MagicMock(
            initial_status="created",
            host=settings.PAYMENT_PROVIDER_NETS_HOST,
            terms_url=settings.PAYMENT_PROVIDER_NETS_TERMS_URL,
            read=MagicMock(return_value=fake_provider_payment),
        )

        mock_get_provider_handler.return_value = mock_nets_provider

        # Invoke the API endpoint
        resp = self.client.post(
            reverse(
                "api-1.0.0:payment_refresh",
                kwargs={"payment_id": test_payment.id},
            ),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )

        self.assertEqual(resp.status_code, 200)
        mock_get_provider_handler.assert_called_once_with("nets")
        mock_nets_provider.read.assert_called_once_with(
            test_payment.provider_payment_id
        )

    @patch("payment.api.get_provider_handler")
    def test_refresh_created_to_reserved(self, mock_get_provider_handler):
        # Test data
        (
            test_payment,
            fake_provider_payment,
        ) = self._create_test_payment_with_fake_provider_payment(
            status="created",
            amount=1337,
            declaration=self.declaration,
            provider_payment_id="1234",
            provider_payment_summary=ProviderPaymentSummaryResponse(
                reserved_amount=1337,
                charged_amount=0,
                refunded_amount=0,
                cancelled_amount=0,
            ),
        )

        # Configure mock(s)
        mock_nets_provider = MagicMock(
            initial_status="created",
            host=settings.PAYMENT_PROVIDER_NETS_HOST,
            terms_url=settings.PAYMENT_PROVIDER_NETS_TERMS_URL,
            read=MagicMock(return_value=fake_provider_payment),
        )

        mock_get_provider_handler.return_value = mock_nets_provider

        # Invoke the API endpoint
        resp = self.client.post(
            reverse(
                "api-1.0.0:payment_refresh",
                kwargs={"payment_id": test_payment.id},
            ),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )
        self.assertEqual(resp.status_code, 200)
        test_payment.refresh_from_db()

        mock_nets_provider.read.assert_called_once_with(
            test_payment.provider_payment_id
        )
        self.assertEqual(test_payment.status, "reserved")

    @patch("payment.api.get_provider_handler")
    def test_refresh_reserved_to_paid(self, mock_get_provider_handler):
        # Test data
        (
            test_payment,
            fake_provider_payment,
        ) = self._create_test_payment_with_fake_provider_payment(
            status="reserved",
            amount=1337,
            declaration=self.declaration,
            provider_payment_id="1234",
            provider_payment_summary=ProviderPaymentSummaryResponse(
                reserved_amount=0,
                charged_amount=1337,
                refunded_amount=0,
                cancelled_amount=0,
            ),
        )

        # Configure mock(s)
        mock_nets_provider = MagicMock(
            initial_status="reserved",
            host=settings.PAYMENT_PROVIDER_NETS_HOST,
            terms_url=settings.PAYMENT_PROVIDER_NETS_TERMS_URL,
            read=MagicMock(return_value=fake_provider_payment),
        )

        mock_get_provider_handler.return_value = mock_nets_provider

        # Invoke the API endpoint
        resp = self.client.post(
            reverse(
                "api-1.0.0:payment_refresh",
                kwargs={"payment_id": test_payment.id},
            ),
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )
        self.assertEqual(resp.status_code, 200)
        test_payment.refresh_from_db()

        mock_nets_provider.read.assert_called_once_with(
            test_payment.provider_payment_id
        )
        self.assertEqual(test_payment.status, "paid")


class PaymentManagementCommandTests(PaymentTest):
    @patch("payment.management.commands.payment_charge_reserved.print")
    @patch("payment.management.commands.payment_charge_reserved.get_provider_handler")
    def test_charge_reserved(self, mock_get_provider_handler, *args):
        # test data
        (
            test_payment_1,
            fake_provider_payment_1,
        ) = self._create_test_payment_with_fake_provider_payment(
            status="reserved",
            amount=1337,
            declaration=self.declaration,
            provider_payment_id="1234",
            provider_payment_summary=ProviderPaymentSummaryResponse(
                reserved_amount=1337,
                charged_amount=0,
                refunded_amount=0,
                cancelled_amount=0,
            ),
        )

        (
            test_payment_2,
            fake_provider_payment_2,
        ) = self._create_test_payment_with_fake_provider_payment(
            status="reserved",
            amount=7331,
            declaration=self.declaration_2,
            provider_payment_id="5678",
            provider_payment_summary=ProviderPaymentSummaryResponse(
                reserved_amount=7331,
                charged_amount=0,
                refunded_amount=0,
                cancelled_amount=0,
            ),
        )

        fake_provider_payments = {
            fake_provider_payment_1.payment_id: fake_provider_payment_1,
            fake_provider_payment_2.payment_id: fake_provider_payment_2,
        }

        # Configure mock(s)
        mock_nets_provider = MagicMock(
            host=settings.PAYMENT_PROVIDER_NETS_HOST,
            terms_url=settings.PAYMENT_PROVIDER_NETS_TERMS_URL,
            read=MagicMock(
                side_effect=lambda x: (
                    fake_provider_payments[x] if x in fake_provider_payments else None
                )
            ),
            charge=MagicMock(side_effect=[None, None]),
        )

        mock_get_provider_handler.return_value = mock_nets_provider

        # Invoke the management command & refresh payments
        call_command("payment_charge_reserved")
        test_payment_1.refresh_from_db()
        test_payment_2.refresh_from_db()

        # Assert everything happend as expected
        mock_nets_provider.read.assert_has_calls(
            [
                call(test_payment_1.provider_payment_id),
                call(test_payment_2.provider_payment_id),
            ]
        )
        mock_nets_provider.charge.assert_has_calls(
            [
                call(test_payment_1.provider_payment_id, test_payment_1.amount),
                call(test_payment_2.provider_payment_id, test_payment_2.amount),
            ]
        )
        self.assertEqual(test_payment_1.status, "paid")
        self.assertEqual(test_payment_2.status, "paid")
