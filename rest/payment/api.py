# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from typing import Callable, Dict, List, Tuple

from anmeldelse.models import PrivatAfgiftsanmeldelse, Varelinje
from django.forms import model_to_dict
from ninja_extra import api_controller, permissions, route
from ninja_extra.exceptions import NotFound
from ninja_jwt.authentication import JWTAuth
from payment.exceptions import InternalPaymentError, PaymentValidationError
from payment.models import Item, Payment
from payment.permissions import PaymentPermission
from payment.provider_handlers import NetsProviderHandler
from payment.schemas import (
    BasePayment,
    PaymentCreatePayload,
    PaymentResponse,
    ProviderPaymentPayload,
)
from project import settings


@api_controller(
    "/payment",
    tags=["payment"],
    permissions=[permissions.IsAuthenticated & PaymentPermission],
)
class PaymentAPI:
    @route.post("", auth=JWTAuth(), url_name="payment_create")
    def create(self, payload: PaymentCreatePayload) -> PaymentResponse:
        declaration = PrivatAfgiftsanmeldelse.objects.get(id=payload.declaration_id)
        if not declaration:
            raise NotFound(f"Failed to fetch declaration: {payload.declaration_id}")

        # Get payment provider handler for this declaration
        provider_handler: NetsProviderHandler = get_provider_handler("nets")

        # Create payment locally, if it does not exist
        payment_new = Payment.objects.filter(
            declaration_id=payload.declaration_id
        ).first()
        if payment_new:
            return payment_model_to_response(
                payment_new,
                field_converts=payment_field_converters(provider_handler, full=True),
            )

        payment_new = Payment.objects.create(
            amount=0,
            currency="DKK",
            reference=payload.declaration_id,
            declaration=declaration,
        )

        # Get declaration "varelinjer" and create payment items
        payment_new_amount = 0
        payment_new_items = []
        for varelinje in Varelinje.objects.filter(
            privatafgiftsanmeldelse_id=payload.declaration_id
        ):
            payment_item = generate_payment_item_from_varelinje(varelinje)
            payment_new_items.append(
                Item.objects.create(**payment_item, payment=payment_new)
            )
            payment_new_amount += payment_item["gross_total_amount"]

        payment_new.amount = payment_new_amount
        payment_new.save()

        # Create provider payment (external)
        provider_payment_payload = ProviderPaymentPayload(
            **model_to_dict(payment_new),
            declaration_id=payment_new.declaration.id,
            items=[model_to_dict(item) for item in payment_new_items],
        )
        provider_payment_validation(provider_payment_payload)

        provider_payment_new = provider_handler.create(
            provider_payment_payload,
            f"{settings.HOST_DOMAIN}/payment/checkout/{declaration.id}",
        )

        # Update local payment with external provider payment info
        payment_new.provider_host = provider_handler.host
        payment_new.provider_payment_id = provider_payment_new["paymentId"]
        payment_new.status = "created"
        payment_new.save()

        return payment_model_to_response(
            payment_new,
            field_converts=payment_field_converters(provider_handler, full=True),
        )

    @route.get("", auth=JWTAuth(), url_name="payment_list")
    def list(self) -> List[PaymentResponse]:
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

        provider_handler = get_provider_handler("nets")
        return [
            payment_model_to_response(
                payment,
                payment_field_converters(
                    provider_handler,
                    full=bool(self.context.request.GET.get("full", None)),
                ),
            )
            for payment in payments
        ]

    @route.get("/{payment_id}", auth=JWTAuth(), url_name="payment_get")
    def get(self, payment_id: int) -> PaymentResponse:
        payment_local = Payment.objects.prefetch_related("items").get(id=payment_id)

        return payment_model_to_response(
            payment_local,
            field_converts=payment_field_converters(
                get_provider_handler("nets"),
                full=bool(self.context.request.GET.get("full", None)),
            ),
        )

    @route.post("/refresh/{payment_id}", auth=JWTAuth(), url_name="payment_refresh")
    def refresh(self, payment_id: int) -> PaymentResponse:
        payment_local = Payment.objects.get(id=payment_id)
        if payment_local.status == "created":
            provider_handler = get_provider_handler("nets")
            provider_payment = provider_handler.read(payment_local.provider_payment_id)

            # Check if payment have been paid
            paymentSummary = provider_payment["summary"]
            if "reservedAmount" in paymentSummary:
                # TODO: refine this when we know how "charged" payments works
                if paymentSummary["reservedAmount"] == payment_local.amount:
                    payment_local.status = "paid"
                    payment_local.save()

        # Default, return the payment without doing anything
        return payment_model_to_response(
            payment_local,
            field_converts=payment_field_converters(
                get_provider_handler("nets"),
                full=True,
            ),
        )


# Helpers


def provider_payment_validation(payment: BasePayment):
    # Make sure the payment amount is equal to the sum of all items gross_total_amount
    # https://developer.nexigroup.com/nexi-checkout/en-EU/api/payment-v1/#v1-payments-post-body-order-amount
    if payment.amount != sum([item.gross_total_amount for item in payment.items]):
        raise PaymentValidationError(
            "Payment amount does not match the sum of all items"
        )


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


def get_provider_handler(provider_name: str) -> NetsProviderHandler:
    if provider_name.lower() == "nets":
        return NetsProviderHandler(secret_key=settings.PAYMENT_PROVIDER_NETS_SECRET_KEY)

    raise InternalPaymentError(f"Unknown provider: {provider_name}")


def payment_field_converters(provider_handler: NetsProviderHandler, full: bool):
    return {
        "declaration": lambda field_value: (
            "declaration",
            PrivatAfgiftsanmeldelse.objects.get(id=field_value)
            if full
            else field_value,
        ),
        "provider_payment_id": lambda field_value: (
            "provider_payment",
            provider_handler.read(field_value) if full else None,
        ),
    }


def generate_payment_item_from_varelinje(
    varelinje: Varelinje, currency_multiplier: int = 100
):
    varelinje_name = varelinje.vareafgiftssats.vareart_da

    quantity = varelinje.antal
    if varelinje.vareafgiftssats.enhed in ["kg", "liter", "l"]:
        quantity = int(varelinje.mængde)

    unit = varelinje.vareafgiftssats.enhed
    unit_price = varelinje.vareafgiftssats.afgiftssats * currency_multiplier

    tax_rate = 0  # DKK is 25 * 100, but greenland is 0
    tax_amount = unit_price * quantity * tax_rate / 10000
    net_total_amount = unit_price * quantity
    gross_total_amount = net_total_amount + tax_amount

    return {
        "reference": varelinje.vareafgiftssats.afgiftsgruppenummer,
        "name": varelinje_name,
        "quantity": quantity,
        "unit": unit,
        "unit_price": int(unit_price),
        "tax_rate": tax_rate,
        "tax_amount": int(tax_amount),
        "gross_total_amount": int(gross_total_amount),
        "net_total_amount": int(net_total_amount),
    }