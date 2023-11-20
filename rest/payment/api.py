# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import requests
from ninja_extra import api_controller, permissions, route
from ninja_jwt.authentication import JWTAuth
from payment.models import Order
from payment.schemas import OrderSchema
from payment.permissions import PaymentPermission
from project import settings


@api_controller(
    "/payment",
    tags=["payment"],
    permissions=[permissions.IsAuthenticated & PaymentPermission],
)
class PaymentAPI:
    @route.post("/create", auth=JWTAuth(), url_name="order_create")
    def create_order(self, payload: OrderSchema):
        payment_order = payload.dict()

        # TODO: Create order locally
        order = Order.objects.create(**payment_order)

        # TODO: Create payment in the provider
        resp = requests.post(
            f"{settings.PAYMENT_PROVIDER_NETS_HOST}/v1/payments",
            json={
                "order": payment_order,
                "checkout": {"termsUrl": settings.PAYMENT_PROVIDER_NETS_TERMS_URL},
            },
        )

        if resp.status_code != 201:
            raise Exception("Failed to create payments")

        return resp.json()
