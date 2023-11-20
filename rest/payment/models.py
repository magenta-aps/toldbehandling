# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from django.db import models


class Item(models.Model):
    """A payment order item

    For more details, see https://developer.nexigroup.com/nexi-checkout/en-EU/api/payment-v1/#v1-payments-post-body-order-items
    """

    reference = models.CharField(max_length=128)
    name = models.CharField(max_length=128)
    quantity = models.IntegerField()
    unit = models.CharField(max_length=128)
    unit_price = models.IntegerField()
    gross_total_amount = models.IntegerField()
    net_total_amount = models.IntegerField()

    order = models.ForeignKey("Order", on_delete=models.DO_NOTHING, related_name='items')


class Order(models.Model):
    """The payment order.

    Based on Nets `payment.order` from their Checkout API v1:
    https://developer.nexigroup.com/nexi-checkout/en-EU/api/payment-v1/#v1-payments-post-body-order
    """

    amount = models.IntegerField()
    currency = models.CharField(max_length=3)
    reference = models.CharField(max_length=128, null=True)
