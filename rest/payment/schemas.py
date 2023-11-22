# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from ninja import ModelSchema, Schema
from payment.models import Item, Order


class ItemSchema(ModelSchema):
    class Config:
        model = Item
        model_fields = [
            "id",
            "reference",
            "name",
            "quantity",
            "unit",
            "unit_price",
            "tax_rate",
            "gross_total_amount",
            "net_total_amount",
        ]


class OrderCreateSchema(ModelSchema):
    items: list[ItemSchema]

    class Config:
        model = Order
        model_fields = [
            "id",
            "amount",
            "currency",
            "reference",
        ]


class PaymentCreateSchema(Schema):
    order: OrderCreateSchema


class PaymentCreateResponse(Schema):
    order: OrderCreateSchema
    provider: dict
