# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from ninja import ModelSchema

from payment.models import Order


class OrderSchema(ModelSchema):
    class Config:
        model = Order
        model_fields = [
            "amount",
            "currency",
            "reference",
        ]
