# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from typing import Optional

from django.utils.translation import gettext_lazy as _
from ninja_extra import status
from ninja_extra.exceptions import APIException


class ProviderPingError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = _(
        (
            "Unable to ping payment provider: {provider_name}, "
            "expected HTTP response code: {expected_status_code}, "
            "but got {actual_status_code}"
        )
    )

    def __init__(
        self,
        provider_name: str,
        expected_status_code: int,
        actual_status_code: int,
    ):
        super().__init__(
            self.default_detail.format(
                provider_name=provider_name,
                expected_status_code=expected_status_code,
                actual_status_code=actual_status_code,
            )
        )


class ProviderHandlerNotFound(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("Payment provider handler not found for: {provider}")
    default_code = "payment_provider_handler_not_found"

    def __init__(self, provider: str):
        self.detail = self.default_detail.format(provider=provider)
        super().__init__(self.detail)


class ProviderPaymentNotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = _(
        "Payment provider payment not found: {payment_id} "
        "- {endpoint} ({endpoint_status})"
    )
    default_code = "payment_provider_payment_not_found"

    def __init__(self, payment_id: Optional[str], endpoint: str, endpoint_status: int):
        self.detail = self.default_detail.format(
            payment_id=payment_id,
            endpoint=endpoint,
            endpoint_status=endpoint_status,
        )
        super().__init__(self.detail)


class ProviderPaymentCreateError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _(
        "Failed creating provider payment: {response_text} "
        "- {endpoint} ({endpoint_status})"
    )
    default_code = "payment_provider_payment_create"

    def __init__(
        self,
        response_text: str,
        endpoint: str,
        endpoint_status: int,
    ):
        self.detail = self.default_detail.format(
            response_text=response_text,
            endpoint=endpoint,
            endpoint_status=endpoint_status,
        )
        super().__init__(self.detail)


class ProviderPaymentChargeError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = _("Payment provider charge error")
    default_code = "payment_provider_charge"


class InternalPaymentError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = _("An internal payment error occured.")
    default_code = "payment_internal"
