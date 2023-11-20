from django import forms
from payments import PaymentStatus
from payments.forms import PaymentForm


class NetsPaymentForm(PaymentForm):
    status = forms.ChoiceField(choices=PaymentStatus.CHOICES, disabled=True)

    # def clean(self):
    #     cleaned_data = super().clean()

    #     if not self.errors:
    #         if not self.payment.transaction_id:
    #             pass

    #         try:
    #             data = self.provider.create_payment(self.payment, cleaned_data)
    #         except Exception as e:

