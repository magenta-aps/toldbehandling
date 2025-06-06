# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from datetime import datetime, timedelta, timezone
from typing import Optional

import requests
from django.conf import settings
from payment.exceptions import (
    ProviderHandlerNotFound,
    ProviderPaymentChargeError,
    ProviderPaymentCreateError,
    ProviderPaymentNotFound,
    ProviderPingError,
)
from payment.schemas import ProviderPaymentPayload, ProviderPaymentResponse
from payment.utils import convert_keys_to_camel_case


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

    def charge(self, payment_id: str, amount: int):
        raise NotImplementedError()

    def ping(self) -> timedelta:
        raise NotImplementedError()

    @property
    def headers(self):
        raise NotImplementedError()


class NetsProviderHandler(ProviderHandler):
    def __init__(self, secret_key: str) -> None:
        self.host = settings.PAYMENT_PROVIDER_NETS_HOST  # type: ignore
        self.terms_url = settings.PAYMENT_PROVIDER_NETS_TERMS_URL  # type: ignore
        self.secret_key = secret_key

    def create(
        self, payload: ProviderPaymentPayload, checkout_url: str
    ) -> ProviderPaymentResponse:
        # Modify payload VARCHARS to match Nets requirements of max 128 chars
        # NOTE: The payment models was made using NETs order.item-object, so
        # all VARCHAR fields are 128 chars long, EXCEPT for the `name` field
        # which i modified to 256 chars long, after seeing us use strings
        # of that length internally.
        for item in payload.items:
            item.name = f"{item.name[:125]}..."  # type: ignore

        url = f"{self.host}/v1/payments"
        response = requests.post(
            url,
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
            raise ProviderPaymentCreateError(
                endpoint=url,
                endpoint_status=response.status_code,
                response_text=response.text,
            )

        resp_body = response.json()
        return self.read(resp_body["paymentId"])

    def read(self, payment_id: Optional[str]) -> ProviderPaymentResponse:
        url = f"{self.host}/v1/payments/{payment_id}"
        resp = requests.get(url, headers=self.headers)

        if resp.status_code != 200:
            raise ProviderPaymentNotFound(
                payment_id=payment_id, endpoint=url, endpoint_status=resp.status_code
            )

        resp_body = resp.json()
        return ProviderPaymentResponse(**resp_body["payment"])

    def charge(self, payment_id: str, amount: int):
        resp = requests.post(
            f"{self.host}/v1/payments/{payment_id}/charges",
            headers=self.headers,
            json={
                "amount": amount,
            },
        )

        if resp.status_code != 201:
            raise ProviderPaymentChargeError(detail=resp.text)

        return resp.json()

    def ping(self) -> timedelta:
        """Pings the provider to check if it's up and running.

        NOTE: NETs does not have a ping endpoint, so we use the "GET /v1/payments"
        and check if we get a 405 status code, which is the expected status code when
        using GET on this endpoint
        """

        now = datetime.now(timezone.utc)
        resp = requests.get(f"{self.host}/v1/payments", headers=self.headers)
        req_resp_time = datetime.now(timezone.utc) - now

        if resp.status_code != 405:
            raise ProviderPingError(
                provider_name=self.__class__.__name__,
                expected_status_code=405,
                actual_status_code=resp.status_code,
            )

        return req_resp_time

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

    def read(self, payment_id: Optional[str]):
        return None

    def ping(self) -> timedelta:
        return timedelta(seconds=0)


def get_provider_handler(
    provider_name: str,
) -> NetsProviderHandler | BankProviderHandler:
    if provider_name.lower() == settings.PAYMENT_PROVIDER_NETS:  # type: ignore
        return NetsProviderHandler(
            secret_key=settings.PAYMENT_PROVIDER_NETS_SECRET_KEY  # type: ignore
        )
    if provider_name.lower() == settings.PAYMENT_PROVIDER_BANK:  # type: ignore
        return BankProviderHandler()

    raise ProviderHandlerNotFound(provider_name)
