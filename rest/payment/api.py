# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import requests
from django.forms import model_to_dict
from ninja_extra import api_controller, permissions, route
from ninja_jwt.authentication import JWTAuth
from payment.models import Item, Order
from payment.permissions import PaymentPermission
from payment.schemas import PaymentCreateResponse, PaymentCreateSchema
from project import settings


@api_controller(
    "/payment",
    tags=["payment"],
    permissions=[permissions.IsAuthenticated & PaymentPermission],
)
class PaymentAPI:
    @route.post("/create", auth=JWTAuth(), url_name="order_create")
    def create(self, payload: PaymentCreateSchema) -> PaymentCreateResponse:
        nets_payment_order = payload.order.dict()

        # Convert nets_payment_order keys from snake_case to camelCase (resursively)
        # The though is python likes "snake_case" and Nets likes "camelCase", and
        # instead of changing python syntax, we convert the keys before sending to Nets
        def convert_keys_to_camel_case(data):
            if isinstance(data, dict):
                new_data = {}
                for key, value in data.items():
                    new_key = "".join(
                        word.capitalize() if i > 0 else word
                        for i, word in enumerate(key.split("_"))
                    )
                    new_data[new_key] = convert_keys_to_camel_case(value)
                return new_data
            elif isinstance(data, list):
                return [convert_keys_to_camel_case(item) for item in data]
            else:
                return data

        nets_payment_order = convert_keys_to_camel_case(nets_payment_order)

        # Create provider payment
        net_resp_create = requests.post(
            f"{settings.PAYMENT_PROVIDER_NETS_HOST}/v1/payments",
            headers={
                # OBS: Nets require this content-type header
                "content-type": "application/*+json",
                "CommercePlatformTag": "SOME_STRING_VALUE",
                "Authorization": f"Bearer {settings.PAYMENT_PROVIDER_NETS_SECRET_KEY}",
            },
            json={
                "order": nets_payment_order,
                "checkout": {
                    "url": "http://localhost:8000/payment/checkout",
                    "termsUrl": settings.PAYMENT_PROVIDER_NETS_TERMS_URL,
                },
            },
        )

        if net_resp_create.status_code != 201:
            raise Exception("Failed to create payments")

        net_payment_create_resp = net_resp_create.json()

        # Get newly created payment from provider
        net_resp_get = requests.get(
            (
                f"{settings.PAYMENT_PROVIDER_NETS_HOST}/v1/payments/",
                f"{net_payment_create_resp['paymentId']}",
            ),
            headers={
                # OBS: Nets require this content-type header
                "content-type": "application/*+json",
                "CommercePlatformTag": "SOME_STRING_VALUE",
                "Authorization": f"Bearer {settings.PAYMENT_PROVIDER_NETS_SECRET_KEY}",
            },
        )

        if net_resp_get.status_code != 200:
            raise Exception(
                f"Failed to fetch payment: {net_payment_create_resp['paymentId']}"
            )

        net_payment_order = net_resp_get.json()

        # Persist order locally
        order = Order.objects.create(
            **{
                "amount": nets_payment_order["amount"],
                "currency": nets_payment_order["currency"],
                "reference": nets_payment_order["reference"],
                "provider_host": settings.PAYMENT_PROVIDER_NETS_HOST,
                "provider_payment_id": net_payment_order["payment"]["paymentId"],
            }
        )

        new_items = []
        for item in payload.order.items:
            new_item = Item.objects.create(
                **{
                    "reference": item.reference,
                    "name": item.name,
                    "quantity": item.quantity,
                    "unit": item.unit,
                    "unit_price": item.unit_price,
                    "tax_rate": item.tax_rate,
                    "gross_total_amount": item.gross_total_amount,
                    "net_total_amount": item.net_total_amount,
                    "order": order,
                }
            )
            new_items.append(model_to_dict(new_item))

        # Create response object
        order_dict = model_to_dict(order)
        order_dict["items"] = new_items

        return {
            "order": order_dict,
            "provider": net_payment_order,
        }
