# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from typing import List

from anmeldelse.models import PrivatAfgiftsanmeldelse
from ninja import ModelSchema, Schema
from payment.models import Item, Payment
from payment.utils import convert_keys_to_snake_case
from project.settings import PAYMENT_PROVIDER_NETS

# Model schemas for models outside the payment-app (e.g. anmeldelse)


class PaymentDeclaration(ModelSchema):
    class Config:
        model = PrivatAfgiftsanmeldelse
        model_fields = [
            "id",
            "oprettet",
            "oprettet_af",
            "oprettet_på_vegne_af",
            "cpr",
            "anonym",
            "navn",
            "adresse",
            "postnummer",
            "by",
            "telefon",
            "bookingnummer",
            "leverandørfaktura_nummer",
            "indførselstilladelse",
            "indleveringsdato",
            "leverandørfaktura",
            "status",
        ]


# Generics


class BaseResponse(Schema):
    def __init__(self, *args, **kwargs):
        super().__init__(**convert_keys_to_snake_case(kwargs))


class BaseItem(ModelSchema):
    class Config:
        model = Item
        model_fields = [
            "reference",
            "name",
            "quantity",
            "unit",
            "unit_price",
            "tax_rate",
            "tax_amount",
            "gross_total_amount",
            "net_total_amount",
        ]


class BasePayment(ModelSchema):
    class Config:
        model = Payment
        model_fields = [
            "amount",
            "currency",
            "reference",
            "provider_host",
            "provider_payment_id",
            "status",
            "declaration",
        ]

    items: List[BaseItem]


class PersistedModel(Schema):
    id: int


class ContactDetails(Schema):
    phone_number: dict


# Input schemas / payloads


class PaymentCreatePayload(Schema):
    declaration_id: int
    provider: str = PAYMENT_PROVIDER_NETS


# Provider input schemas / payloads


class ProviderPaymentPayload(BasePayment):
    pass


# Provider response schemas


class ProviderPaymentSummaryResponse(BaseResponse):
    reserved_amount: int
    charged_amount: int
    refunded_amount: int
    cancelled_amount: int


class ProviderPaymentDetailsResponse(BaseResponse):
    payment_type: str | None
    payment_method: str | None
    invoice_details: dict
    card_details: dict


class ProviderOrderDetailsResponse(BaseResponse):
    amount: int
    currency: str
    reference: str


class ProviderCompanyResponse(BaseResponse):
    contact_details: ContactDetails


class ProviderConsumerResponse(BaseResponse):
    shipping_address: dict
    company: ProviderCompanyResponse
    private_person: ContactDetails
    billing_address: dict


class ProviderPaymentCheckoutResponse(BaseResponse):
    url: str
    cancel_url: str


class ProviderPaymentResponse(BaseResponse):
    payment_id: str
    summary: ProviderPaymentSummaryResponse
    consumer: ProviderConsumerResponse
    payment_details: ProviderPaymentDetailsResponse
    order_details: ProviderOrderDetailsResponse
    checkout: ProviderPaymentCheckoutResponse
    created: str


# Payment response schemas


class PaymentDeclarationResponse(BaseResponse, PaymentDeclaration):
    pass


class PaymentItemResponse(BaseItem, PersistedModel):
    pass


class PaymentResponse(BaseResponse, BasePayment, PersistedModel):
    declaration: PaymentDeclarationResponse
    provider_payment: ProviderPaymentResponse | None
