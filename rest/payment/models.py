# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from django.db import models


class Item(models.Model):
    """A payment item

    The model is based on Nets order.item-object. For more details, see
    https://developer.nexigroup.com/nexi-checkout/en-EU/api/payment-v1/
    """

    reference = models.CharField(max_length=128)
    """A reference to recognize the product, usually the SKU (stock keeping unit) of
    the product. For convenience in the case of refunds or modifications of placed
    orders, the reference should be unique for each variation of a product item
    (size, color, etc).

    Length: 0-128

    The following special characters are not supported: `<,>,\\\\`"""

    name = models.CharField()
    """The name of the product.

    Length: 0-128

    The following special characters are not supported: `<,>,\\\\`"""

    quantity = models.FloatField()
    """The quantity of the product.

    Allowed: >=0"""

    unit = models.CharField(max_length=128)
    """The defined unit of measurement for the product, for example pcs, liters, or kg.

    The following special characters are not supported: `<,>,\\,’,”,&,\\\\`"""

    unit_price = models.IntegerField()
    """The price per unit excluding VAT.

    Note: The amount can be negative."""

    tax_rate = models.IntegerField(default=0)
    """The tax/VAT rate (in percentage times 100). For example, the value `2500`
    corresponds to 25%. Defaults to 0 if not provided.

    Allowed: >=0 & <=99999"""

    tax_amount = models.IntegerField(default=0)
    """The tax/VAT amount (`unitPrice` * `quantity` * `taxRate` / 10000).
    Defaults to 0 if not provided.
    `tax_amount` should include the total tax amount for the entire payment item."""

    gross_total_amount = models.IntegerField()
    """The total amount including VAT (`netTotalAmount` + `taxAmount`).

    Note: The amount can be negative."""

    net_total_amount = models.IntegerField()
    """The total amount excluding VAT (`unitPrice` * `quantity`).

    Note: The amount can be negative."""

    payment = models.ForeignKey(
        "Payment", on_delete=models.CASCADE, related_name="items"
    )
    """The payment the item is related to."""


class Payment(models.Model):
    """The payment model.

    The model is based on Nets order-object. For more details, see
    https://developer.nexigroup.com/nexi-checkout/en-EU/api/payment-v1/
    """

    amount = models.IntegerField()
    """The total amount of the order including VAT, if any. (Sum of all
    grossTotalAmounts in the order.)

    Allowed: >0"""

    currency = models.CharField(max_length=3)
    """The currency of the payment, for example 'SEK'.

    Length: 3

    The following special characters are not supported: `<,>,\\,’,”,&,\\\\`"""

    reference = models.CharField(max_length=128, null=True)
    """A reference to recognize this order. Usually a number sequence (order number).

    Length: 0-128

    The following special characters are not supported: <,>,\\,’,”,&,\\\\"""

    provider_host = models.CharField(max_length=128, null=True)
    """The hostname of the provider, the payment was made through."""

    provider_payment_id = models.CharField(max_length=128, null=True)
    """The payment id from the provider."""

    declaration = models.ForeignKey(
        "anmeldelse.privatafgiftsanmeldelse",
        on_delete=models.DO_NOTHING,
        related_name="payments",
    )
    """The declaration/anmeldelse the payment is related to."""

    status = models.CharField(max_length=128, null=True)
    """created, reserved, paid, declined"""
