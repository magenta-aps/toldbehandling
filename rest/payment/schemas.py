# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from typing import List

from ninja import ModelSchema, Schema
from payment.models import Item, Payment
from project.util import convert_keys_to_snake_case

# Generics


# class BasePayload(Schema):
#     def __init__(self, **data):
#         super().__init__(**convert_keys_to_camel_case(data))


class BaseResponse(Schema):
    def __init__(self, **data):
        super().__init__(**convert_keys_to_snake_case(data))


class PersistedModel(Schema):
    id: int


class ContactDetails(Schema):
    phone_number: dict


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
            "gross_total_amount",
            "net_total_amount",
        ]


class BasePaymentSchema(ModelSchema):
    class Config:
        model = Payment
        model_fields = [
            "amount",
            "currency",
            "reference",
            "provider_host",
            "provider_payment_id",
        ]

    items: List[BaseItem]
    declaration_id: int


# Input schemas / payloads


class PaymentItemCreatePayload(BaseItem):
    pass


class PaymentCreatePayload(BasePaymentSchema):
    pass


class PaymentUpdatePayload(BasePaymentSchema, PersistedModel):
    pass


class PaymentDeletePayload(PersistedModel):
    pass


# Response schemas


class ProviderPaymentDetailsResponse(BaseResponse):
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


class ProviderPaymentResponse(BaseResponse):
    payment_id: str
    payment_details: ProviderPaymentDetailsResponse
    order_details: ProviderOrderDetailsResponse
    consumer: ProviderConsumerResponse
    checkout: dict
    created: str


class PaymentItemResponse(BaseItem, PersistedModel):
    pass


class PaymentResponse(BasePaymentSchema, PersistedModel, BaseResponse):
    items: List[PaymentItemResponse] | None
    provider_payment: ProviderPaymentResponse | None


# class PaymentResponse(BaseResponse, PaymentCreatePayload, PersistedModel):
#     provider_payment: ProviderPaymentResponse
