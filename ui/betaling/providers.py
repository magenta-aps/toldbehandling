from payments.core import BasicProvider
from betaling.forms import NetsPaymentForm


class NetsPaymentProvider(BasicProvider):
    def __init__(self, host, secret_key, checkout_key, capture=True):
        self.host = host
        self.secret_key = secret_key
        self.checkout_key = checkout_key
        super().__init__(capture=capture)

    def get_form(self, payment, data=None):
        form = NetsPaymentForm(
            data=data, hidden_inputs=False, provider=self, payment=payment
        )

        if form.is_valid():
            # do stuff
            pass

        return form

    def process_data(self, payment, request):
        # Implement webhook processing logic
        pass

    def capture(self, payment, amount=None):
        # Implement payment capture logic
        raise NotImplementedError("Capture method not implemented.")

    def refund(self, payment, amount=None):
        # Implement payment refund logic
        raise NotImplementedError("Refund method not implemented.")
