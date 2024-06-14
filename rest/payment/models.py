# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from django.conf import settings
from django.db import models

PAYMENT_PROVIDER_CHOICES = {
    settings.PAYMENT_PROVIDER_NETS: "Nets",
    settings.PAYMENT_PROVIDER_BANK: "Bankoverførsel",
}


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

    created = models.DateTimeField(auto_now_add=True)
    """The time the row was created.

    OBS: "auto_now_add" is used to set the field to now when the object is first created:
    https://docs.djangoproject.com/en/dev/ref/models/fields/#django.db.models.DateField.auto_now_add # noqa
    """

    updated = models.DateTimeField(auto_now=True)
    """The time the row was last updated.

    OBS: "auto_now" is used to set the field to now every time the object is saved:
    https://docs.djangoproject.com/en/dev/ref/models/fields/#django.db.models.DateField.auto_now # noqa
    """

    def __str__(self):
        return f"PaymentItem(payment={self.payment.id}, name={self.name})"


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

    provider = models.CharField(
        max_length=128,
        null=False,
        choices=PAYMENT_PROVIDER_CHOICES.items(),
        default=settings.PAYMENT_PROVIDER_NETS,
    )
    """The payment provider, for example 'nets' or 'bank'."""

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

    created = models.DateTimeField(auto_now_add=True)
    """The time the row was created.

    OBS: "auto_now_add" is used to set the field to now when the object is first created:
    https://docs.djangoproject.com/en/dev/ref/models/fields/#django.db.models.DateField.auto_now_add # noqa
    """

    updated = models.DateTimeField(auto_now=True)
    """The time the row was last updated.

    OBS: "auto_now" is used to set the field to now every time the object is saved:
    https://docs.djangoproject.com/en/dev/ref/models/fields/#django.db.models.DateField.auto_now # noqa
    """

    def __str__(self):
        return (
            f"Payment(id={self.id}, "
            f"tf5={self.declaration.id}, "
            f"status={self.status})"
        )
