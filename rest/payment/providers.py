import requests
from payment.exceptions import ProviderPaymentNotFound
from payment.schemas import PaymentCreatePayload
from project import settings
from project.util import convert_keys_to_camel_case


class NetsProvider:
    def __init__(self, secret_key: str) -> None:
        self.host = settings.PAYMENT_PROVIDER_NETS_HOST
        self.terms_url = settings.PAYMENT_PROVIDER_NETS_TERMS_URL
        self.secret_key = secret_key

    def create(self, payload: PaymentCreatePayload, checkout_url: str):
        resp = requests.post(
            f"{self.host}/v1/payments",
            headers=self._get_headers(),
            json={
                "order": convert_keys_to_camel_case(payload.dict()),
                "checkout": {
                    "url": checkout_url,
                    "termsUrl": self.terms_url,
                },
            },
        )

        if resp.status_code != 201:
            raise Exception("Failed to create payments")

        resp_body = resp.json()
        return self.read(resp_body["paymentId"])

    def read(self, payment_id: str):
        url = f"{self.host}/v1/payments/{payment_id}"
        resp = requests.get(
            url,
            headers=self._get_headers(),
        )

        if resp.status_code != 200:
            raise ProviderPaymentNotFound(payment_id)

        resp_body = resp.json()
        return resp_body["payment"]

    def update(self):
        pass

    def delete(self):
        pass

    def _get_headers(self):
        return {
            # OBS: Nets require this, *+json, content-type header
            "content-type": "application/*+json",
            # "CommercePlatformTag": "SOME_STRING_VALUE",
            "Authorization": f"Bearer {self.secret_key}",
        }
