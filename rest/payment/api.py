# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from typing import Callable, Dict, List, Tuple

from anmeldelse.models import PrivatAfgiftsanmeldelse, Varelinje
from common.api import get_auth_methods
from django.conf import settings
from django.forms import model_to_dict
from ninja_extra import api_controller, permissions, route
from ninja_extra.exceptions import PermissionDenied, ValidationError
from ninja_jwt.authentication import JWTAuth
from payment.models import Item, Payment
from payment.permissions import PaymentPermission
from payment.provider_handlers import (
    NetsProviderHandler,
    ProviderHandler,
    get_provider_handler,
)
from payment.schemas import (
    PaymentCreatePayload,
    PaymentResponse,
    ProviderPaymentPayload,
    ProviderPaymentResponse,
)
from payment.utils import generate_payment_item_from_varelinje, get_payment_fees


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
                return _payment_model_to_response(
                    payment_new,
                    field_converts=_payment_field_converters(provider_handler),
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

        return _payment_model_to_response(
            payment_new,
            field_converts=_payment_field_converters(provider_handler),
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
            _payment_model_to_response(
                payment,
                _payment_field_converters(provider_handler),
            )
            for payment in payments
        ]

    @route.get("/{payment_id}", auth=JWTAuth(), url_name="payment_get")
    def get(self, payment_id: int) -> PaymentResponse:
        payment_local = Payment.objects.prefetch_related("items").get(id=payment_id)

        return _payment_model_to_response(
            payment_local,
            field_converts=_payment_field_converters(
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
        return _payment_model_to_response(
            payment_local,
            field_converts=_payment_field_converters(
                provider_handler, provider_payment
            ),
        )


def _payment_field_converters(
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


def _payment_model_to_response(
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
