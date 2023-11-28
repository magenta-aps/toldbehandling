#
# IMPORTANT!!
# Temporary file for payment stuff, which needs to be moved to told_common, when i figure out a good way
#

from told_common.rest_client import ModelRestClient


class PaymentRestClient(ModelRestClient):
    def create(self):
        data = {
            "items": [
                {
                    "reference": "test_product_3",
                    "name": "Test Produkt 3",
                    "quantity": 1,
                    "unit": "stk",
                    "unit_price": 100,
                    "tax_rate": 2500,
                    "tax_amount": 25,
                    "gross_total_amount": 125,
                    "net_total_amount": 100,
                }
            ],
            "amount": 125,
            "currency": "DKK",
            "reference": "thor-tester-payment-order-3",
            "declaration_id": 101,
        }

        raise NotImplementedError("PaymentRestClient.create not implemented")
        # return self.rest.post("payment", data=data)

    def get(self, payment_id: int):
        return self.rest.get(f"payment/{id}")

    def get_by_declaration(self, declaration_id: int):
        return self.rest.get(f"payment?declaration_id={declaration_id}")
