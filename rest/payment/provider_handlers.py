# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import requests
from payment.exceptions import InternalPaymentError, ProviderPaymentNotFound
from payment.schemas import ProviderPaymentPayload
from payment.utils import convert_keys_to_camel_case
from project import settings


class ProviderHandler:
    initial_status = "created"

    def create(self, payload: ProviderPaymentPayload, checkout_url: str):
        raise NotImplementedError()

    def update(self):
        raise NotImplementedError()

    def delete(self):
        raise NotImplementedError()

    def read(self, payment_id: str):
        raise NotImplementedError()

    @property
    def headers(self):
        raise NotImplementedError()


class NetsProviderHandler(ProviderHandler):
    def __init__(self, secret_key: str) -> None:
        self.host = settings.PAYMENT_PROVIDER_NETS_HOST
        self.terms_url = settings.PAYMENT_PROVIDER_NETS_TERMS_URL
        self.secret_key = secret_key

    def create(self, payload: ProviderPaymentPayload, checkout_url: str):
        # Modify payload VARCHARS to match Nets requirements of max 128 chars
        # NOTE: The payment models was made using NETs order.item-object, so
        # all VARCHAR fields are 128 chars long, EXCEPT for the `name` field
        # which i modified to 256 chars long, after seeing us use strings
        # of that length internally.
        for item in payload.items:
            item.name = f"{item.name[:125]}..."

        response = requests.post(
            f"{self.host}/v1/payments",
            headers=self.headers,
            json={
                # OBS: NETs requires camelCase keys
                "order": convert_keys_to_camel_case(payload.dict()),
                "checkout": {
                    "url": checkout_url,
                    "termsUrl": self.terms_url,
                },
            },
        )

        if response.status_code != 201:
            raise Exception("Failed to create payment: " + response.text)

        resp_body = response.json()
        return self.read(resp_body["paymentId"])

    def read(self, payment_id: str):
        resp = requests.get(
            f"{self.host}/v1/payments/{payment_id}",
            headers=self.headers,
        )

        if resp.status_code != 200:
            raise ProviderPaymentNotFound(payment_id)

        resp_body = resp.json()
        return resp_body["payment"]

    @property
    def headers(self):
        return {
            # OBS: Nets require this, *+json, content-type header
            "content-type": "application/*+json",
            "Authorization": f"Bearer {self.secret_key}",
        }


class BankProviderHandler(ProviderHandler):
    host = None
    initial_status = "paid"

    def create(self, payload: ProviderPaymentPayload, checkout_url: str):
        return {"paymentId": "Der er foretaget en bankoverførsel"}

    def read(self, payment_id: str):
        return None


def get_provider_handler(provider_name: str) -> NetsProviderHandler:
    if provider_name.lower() == settings.PAYMENT_PROVIDER_NETS:
        return NetsProviderHandler(secret_key=settings.PAYMENT_PROVIDER_NETS_SECRET_KEY)
    if provider_name.lower() == settings.PAYMENT_PROVIDER_BANK:
        return BankProviderHandler()
    raise InternalPaymentError(f"Unknown provider: {provider_name}")
