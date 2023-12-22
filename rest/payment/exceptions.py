# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from django.utils.translation import gettext_lazy as _
from ninja_extra import status
from ninja_extra.exceptions import APIException, NotFound


class ProviderPaymentNotFound(NotFound):
    default_detail = _('Provider payment with ID "{payment_id}", not found')
    default_code = "payment_provider_payment_not_found"

    def __init__(self, payment_id: str):
        self.detail = self.default_detail.format(payment_id=payment_id)
        super().__init__(self.detail)


class PaymentValidationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("Payment validation error.")
    default_code = "payment_validation"


class InternalPaymentError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = _("An internal payment error occured.")
    default_code = "payment_internal"
