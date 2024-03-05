# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from decimal import ROUND_HALF_EVEN, Decimal
from typing import Callable, Dict, List, Tuple

from anmeldelse.models import PrivatAfgiftsanmeldelse, Varelinje
from common.api import get_auth_methods
from django.conf import settings
from django.forms import model_to_dict
from ninja_extra import api_controller, permissions, route
from ninja_extra.exceptions import PermissionDenied, ValidationError
from ninja_jwt.authentication import JWTAuth
from payment.exceptions import PaymentValidationError
from payment.models import Item, Payment
from payment.permissions import PaymentPermission
from payment.provider_handlers import (
    NetsProviderHandler,
    ProviderHandler,
    get_provider_handler,
)
from payment.schemas import (
    BasePayment,
    PaymentCreatePayload,
    PaymentResponse,
    ProviderPaymentPayload,
    ProviderPaymentResponse,
)
from payment.utils import round_decimal


@api_controller(
    "/payment",
    tags=["payment"],
    permissions=[permissions.IsAuthenticated & PaymentPermission],
)
class PaymentAPI:
    @route.post(
        "",
        auth=get_auth_methods(),
        url_name="payment_create",
        response={201: PaymentResponse},
    )
    def create(self, payload: PaymentCreatePayload) -> PaymentResponse:
        # Validate payload
        if payload.provider not in (
            settings.PAYMENT_PROVIDER_NETS,
            settings.PAYMENT_PROVIDER_BANK,
        ):
            raise ValidationError(f"Invalid payment provider: {payload.provider}")

        try:
            declaration = PrivatAfgiftsanmeldelse.objects.get(id=payload.declaration_id)
        except PrivatAfgiftsanmeldelse.DoesNotExist:
            raise ValidationError(
                f"Failed to fetch declaration: {payload.declaration_id}"
            )

        if payload.provider == settings.PAYMENT_PROVIDER_BANK:
            if not self.context.request.user.has_perm("payment.bank_payment"):
                raise PermissionDenied

        provider_handler: ProviderHandler = get_provider_handler(payload.provider)

        # Create payment locally, if it does not exist
        try:
            payment_new = Payment.objects.get(
                declaration_id=payload.declaration_id, provider_payment_id__isnull=False
            )
            if payment_new.provider_payment_id is not None:
                return payment_model_to_response(
                    payment_new,
                    field_converts=payment_field_converters(provider_handler),
                )
        except Payment.DoesNotExist:
            pass

        payment_new = Payment.objects.create(
            amount=0,
            currency="DKK",
            reference=payload.declaration_id,
            declaration=declaration,
            provider=payload.provider,
        )

        varelinjer = Varelinje.objects.filter(
            privatafgiftsanmeldelse_id=payload.declaration_id
        )

        # Create provider payment items from varelinjer
        payment_new_amount = 0
        payment_new_items = []
        for varelinje in varelinjer:
            payment_item = generate_payment_item_from_varelinje(varelinje)
            payment_new_items.append(
                Item.objects.create(**payment_item, payment=payment_new)
            )
            payment_new_amount += payment_item["gross_total_amount"]

        # add additional NETs-items to payment,
        # ex.: "tillægsafgift" and "ekspeditionsgebyr"
        payment_fees = get_payment_fees(varelinjer)
        for fee in payment_fees.values():
            payment_new_items.append(Item.objects.create(**fee, payment=payment_new))
            payment_new_amount += fee["gross_total_amount"]

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

        # Update local payment with external provider payment info,
        # after creating the payment at the provider
        payment_new.provider = payload.provider
        payment_new.provider_host = provider_handler.host
        payment_new.provider_payment_id = provider_payment_new.payment_id
        payment_new.status = provider_handler.initial_status
        payment_new.save()

        return payment_model_to_response(
            payment_new,
            field_converts=payment_field_converters(provider_handler),
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

        provider_handler = get_provider_handler(settings.PAYMENT_PROVIDER_NETS)
        return [
            payment_model_to_response(
                payment,
                payment_field_converters(provider_handler),
            )
            for payment in payments
        ]

    @route.get("/{payment_id}", auth=JWTAuth(), url_name="payment_get")
    def get(self, payment_id: int) -> PaymentResponse:
        payment_local = Payment.objects.prefetch_related("items").get(id=payment_id)

        return payment_model_to_response(
            payment_local,
            field_converts=payment_field_converters(
                get_provider_handler(settings.PAYMENT_PROVIDER_NETS),
            ),
        )

    @route.post("/refresh/{payment_id}", auth=JWTAuth(), url_name="payment_refresh")
    def refresh(self, payment_id: int) -> PaymentResponse:
        payment_local = Payment.objects.get(id=payment_id)

        provider_handler = get_provider_handler(settings.PAYMENT_PROVIDER_NETS)
        provider_payment = provider_handler.read(payment_local.provider_payment_id)

        # Update local payment status based on the summary
        if (
            payment_local.status == "created"
            and provider_payment.summary.reserved_amount == payment_local.amount
        ):
            payment_local.status = "reserved"
            payment_local.save()

        if (
            payment_local.status == "reserved"
            and provider_payment.summary.charged_amount == payment_local.amount
        ):
            payment_local.status = "paid"
            payment_local.save()

        # Default, return the payment without doing anything
        return payment_model_to_response(
            payment_local,
            field_converts=payment_field_converters(provider_handler, provider_payment),
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


def payment_field_converters(
    provider_handler: NetsProviderHandler,
    provider_payment: ProviderPaymentResponse | None = None,
):
    return {
        "declaration": lambda field_value: (
            "declaration",
            PrivatAfgiftsanmeldelse.objects.get(id=field_value),
        ),
        "provider_payment_id": lambda field_value: (
            "provider_payment",
            (
                provider_payment
                if provider_payment
                else provider_handler.read(field_value)
            ),
        ),
    }


def generate_payment_item_from_varelinje(
    varelinje: Varelinje, currency_multiplier: int = 100
):
    varelinje_name = varelinje.vareafgiftssats.vareart_da

    quantity = varelinje.antal
    if varelinje.vareafgiftssats.enhed in ["kg", "liter", "l"]:
        quantity = float(varelinje.mængde)

    unit = varelinje.vareafgiftssats.enhed
    unit_price = float(varelinje.vareafgiftssats.afgiftssats * currency_multiplier)

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


def get_payment_fees(varelinjer: List[Varelinje], currency_multiplier: int = 100):
    tillaegsafgift = round_decimal(
        Decimal(settings.TILLAEGSAFGIFT_FAKTOR)
        * sum(
            [
                varelinje.afgiftsbeløb
                for varelinje in varelinjer or []
                if varelinje.vareafgiftssats.har_privat_tillægsafgift_alkohol
            ]
        )
    )

    # OBS: logic copied from "told_common/util.py::round_decimal", but since rest
    # dont have access to told_common tools anymore, its needs to be copied here
    ekspeditionsgebyr = Decimal(
        Decimal(settings.EKSPEDITIONSGEBYR).quantize(
            Decimal(".01"), rounding=ROUND_HALF_EVEN
        )
    )

    return {
        "tillægsafgift": create_nets_payment_item(
            "Tillægsafgift",
            tillaegsafgift,
            reference="tillægsafgift",
        ),
        "ekspeditionsgebyr": create_nets_payment_item(
            "Ekspeditionsgebyr",
            ekspeditionsgebyr,
            reference="ekspeditionsgebyr",
        ),
    }


def create_nets_payment_item(
    name: str,
    price: float,
    unit: str = "ant",
    quantity: int = 1,
    reference="",
    currency_multiplier: int = 100,
):
    unit_price = float(price * currency_multiplier)

    tax_rate = 0  # DKK is 25 * 100, but greenland is 0
    tax_amount = unit_price * quantity * tax_rate / 10000

    net_total_amount = unit_price * quantity
    gross_total_amount = net_total_amount + tax_amount

    return {
        "reference": reference,
        "name": name,
        "quantity": quantity,
        "unit": unit,
        "unit_price": unit_price,
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "gross_total_amount": int(gross_total_amount),
        "net_total_amount": int(net_total_amount),
    }
