# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from decimal import Decimal
from typing import Iterable

from payments import PurchasedItem
from payments.models import BasePayment
from project import settings as project_settings


class Payment(BasePayment):
    def get_failure_url(self) -> str:
        # Return a URL where users are redirected after
        # they fail to complete a payment:
        return f"http://{project_settings.PAYMENT_HOST}/payments/{self.pk}/failure"

    def get_success_url(self) -> str:
        # Return a URL where users are redirected after
        # they successfully complete a payment:
        return f"http://{project_settings.PAYMENT_HOST}/payments/{self.pk}/success"

    def get_purchased_items(self) -> Iterable[PurchasedItem]:
        # Return items that will be included in this payment.
        yield PurchasedItem(
            name="The Hound of the Baskervilles",
            sku="BSKV",
            quantity=9,
            price=Decimal(10),
            currency="USD",
        )
