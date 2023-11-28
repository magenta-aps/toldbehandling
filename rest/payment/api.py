# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from typing import Any, Callable, Dict, List, Tuple

from django.conf.locale import de
from django.forms import model_to_dict
from ninja_extra import api_controller, permissions, route
from ninja_extra.exceptions import NotFound
from ninja_jwt.authentication import JWTAuth
from payment.exceptions import InternalPaymentError, PaymentValidationError
from payment.models import Item, Payment
from payment.permissions import PaymentPermission
from payment.providers import NetsProvider
from payment.schemas import (
    BasePaymentSchema,
    PaymentCreatePayload,
    PaymentResponse,
    ProviderPaymentResponse,
)
from project import settings


@api_controller(
    "/payment",
    tags=["payment"],
    permissions=[permissions.IsAuthenticated & PaymentPermission],
)
class PaymentAPI:
    @route.get("", auth=JWTAuth(), url_name="payment_list")
    def list(self) -> List[PaymentResponse]:
        # Configure filter
        payment_filter = {}
        declaration_id = self.context.request.GET.get("declaration", None)
        if declaration_id:
            payment_filter["declaration_id"] = declaration_id

        # Fetch the payments + check if we need to do a full fetch / include relations
        full = bool(self.context.request.GET.get("full", None))
        payments = (
            Payment.objects.filter(**payment_filter)
            if not full
            else Payment.objects.prefetch_related("items").filter(**payment_filter)
        )

        return [
            payment_model_to_response(
                payment,
                self._payment_field_converters(
                    self._get_provider_handler("nets"),
                    full=bool(self.context.request.GET.get("full", None)),
                ),
            )
            for payment in payments
        ]

    @route.post("", auth=JWTAuth(), url_name="payment_create")
    def create(self, payload: PaymentCreatePayload) -> PaymentResponse:
        self._payment_schema_validation(payload)

        # First, create local payment, since the ID is needed for NETs checkout flow
        payment_new = Payment.objects.create(
            amount=payload.amount,
            currency=payload.currency,
            reference=payload.reference,
            declaration_id=payload.declaration_id,
        )

        # Create provider payment
        provider_handler: NetsProvider = self._get_provider_handler("nets")
        provider_payment_new = provider_handler.create(
            payload=payload,
            checkout_url=f"{settings.HOST_DOMAIN}/payment/checkout/{payload.declaration_id}",
        )

        # Update local payment with provider_host & provider_payment_id (transparency)
        payment_new.provider_host = provider_handler.host
        payment_new.provider_payment_id = provider_payment_new["paymentId"]
        payment_new.save()

        new_items = []
        for item in payload.items:
            new_item = Item.objects.create(**item.dict(), payment=payment_new)
            new_items.append(model_to_dict(new_item))

        return payment_model_to_response(
            payment_new,
            field_converts=self._payment_field_converters(
                self._get_provider_handler("nets"),
                full=True,
            ),
        )

    @route.get("/{payment_id}", auth=JWTAuth(), url_name="payment_get")
    def get(self, payment_id: int) -> PaymentResponse:
        try:
            payment_local = Payment.objects.prefetch_related("items").get(id=payment_id)
        except Payment.DoesNotExist:
            raise NotFound(f"Failed to fetch local payment: {payment_id}")

        return payment_model_to_response(
            payment_local,
            field_converts=self._payment_field_converters(
                self._get_provider_handler("nets"),
                full=bool(self.context.request.GET.get("full", None)),
            ),
        )

    def _payment_field_converters(self, nets_provider: NetsProvider, full: bool):
        return {
            "declaration": lambda field_value: ("declaration_id", field_value),
            "provider_payment_id": lambda field_value: (
                "provider_payment",
                nets_provider.read(field_value) if full else None,
            ),
        }

    def _payment_schema_validation(self, payment: BasePaymentSchema):
        # Make sure the payment amount is equal to the sum of all items gross_total_amount
        # https://developer.nexigroup.com/nexi-checkout/en-EU/api/payment-v1/#v1-payments-post-body-order-amount
        if payment.amount != sum([item.gross_total_amount for item in payment.items]):
            raise PaymentValidationError(
                "Payment amount does not match the sum of all items"
            )

    def _get_provider_handler(self, provider_name: str) -> Any:
        if provider_name.lower() == "nets":
            return NetsProvider(secret_key=settings.PAYMENT_PROVIDER_NETS_SECRET_KEY)

        raise InternalPaymentError(f"Unknown provider: {provider_name}")


def payment_model_to_response(
    payment_model: Payment,
    field_converts: Dict[str, Callable[[str | int], Tuple[str, str]]] | None,
) -> PaymentResponse:
    payment_local_dict = model_to_dict(payment_model)

    if payment_model.items:
        payment_local_dict["items"] = [
            model_to_dict(item) for item in payment_model.items.all()
        ]

    if field_converts and len(field_converts.keys()) > 0:
        for field, convert in field_converts.items():
            field_with_converted_val, converted_value = convert(
                payment_local_dict[field]
            )
            if converted_value is not None:
                payment_local_dict[field_with_converted_val] = converted_value

    return PaymentResponse(**payment_local_dict)
