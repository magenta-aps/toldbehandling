# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from django.db import models


class Item(models.Model):
    """A payment item

    For more details, see
    https://developer.nexigroup.com/nexi-checkout/en-EU/api/payment-v1/
    """

    reference = models.CharField(max_length=128)
    name = models.CharField(max_length=128)
    quantity = models.IntegerField()

    unit = models.CharField(max_length=128)
    """The defined unit of measurement for the product, for example pcs, liters, or kg.
    
    The following special characters are not supported: `<,>,\\,’,”,&,\\\\`"""

    unit_price = models.IntegerField()
    """The price per unit excluding VAT.
    
    Note: The amount can be negative."""

    tax_rate = models.IntegerField(default=0)
    """The tax/VAT rate (in percentage times 100). For examlpe, the value `2500` corresponds to 25%. Defaults to 0 if not provided.
    
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


class Payment(models.Model):
    """The payment model.

    Based on Nets `payment.order` from their Checkout API v1:
    https://developer.nexigroup.com/nexi-checkout/en-EU/api/payment-v1/#v1-payments-post-body-order
    """

    amount = models.IntegerField()
    """The total amount of the order including VAT, if any. (Sum of all grossTotalAmounts in the order.)
    
    Allowed: >0"""

    currency = models.CharField(max_length=3)
    """The currency of the payment, for example 'SEK'.
    
    Length: 3
    
    The following special characters are not supported: `<,>,\\,’,”,&,\\\\`"""

    reference = models.CharField(max_length=128, null=True)
    """A reference to recognize this order. Usually a number sequence (order number).

    Length: 0-128

    The following special characters are not supported: <,>,\,’,”,&,\\"""

    # DB relation field(s)
    declaration = models.ForeignKey(
        "anmeldelse.Afgiftsanmeldelse",
        on_delete=models.DO_NOTHING,
        related_name="payments",
    )

    # Third party provider fields
    provider_host = models.CharField(max_length=128, null=True)
    provider_payment_id = models.CharField(max_length=128, null=True)
