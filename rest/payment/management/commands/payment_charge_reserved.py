from anmeldelse.models import PrivatAfgiftsanmeldelse
from django.conf import settings
from django.core.management.base import BaseCommand
from payment.exceptions import ProviderPaymentChargeError, ProviderPaymentNotFound
from payment.models import Payment
from payment.provider_handlers import get_provider_handler


class Command(BaseCommand):
    """
    Command which goes through all reserved payments and charges them
    """

    help = "Charge payments that have been reserved"

    def handle(self, *args, **kwargs):
        # Check if there is payments to charge
        reserved_payments = Payment.objects.filter(status="reserved")
        print(f"{reserved_payments.count()} reserved payments to charge...")
        for payment in reserved_payments:
            print(f"- Charging payment {payment.id} ({payment.provider_payment_id})...")
            provider_handler = get_provider_handler(payment.provider)
            payment_tf5 = PrivatAfgiftsanmeldelse.objects.get(id=payment.declaration.id)

            # Fetch the payment from third party, and verify they are in sync
            try:
                provider_payment = provider_handler.read(payment.provider_payment_id)
            except ProviderPaymentNotFound:
                provider_payment = None

            if provider_payment is None:
                print(f"  Payment {payment.id} not found at provider, skipping!")
                continue

            # Skip the payment if it's not in sync with the provider
            if provider_payment.summary.reserved_amount != payment.amount:
                print(
                    f"  WARNING: out of sync with the payment_provider "
                    f"({provider_payment.summary.reserved_amount} != {payment.amount})"
                )
                continue

            # Charge the payment
            try:
                _ = provider_handler.charge(payment.provider_payment_id, payment.amount)
            except ProviderPaymentChargeError as e:
                if (
                    f"cannot overcharge payment. reserved amount: {payment.amount}. "
                    f"previously charged amount: {payment.amount}. "
                    f"tried to charge: {payment.amount}"
                ) in e.detail.lower():
                    print(
                        (
                            f'  Payment "{payment.id}", for TF5 '
                            f'"{payment.declaration.id}", '
                            f"have already been charged. Setting payment.status to "
                            f'"{settings.PAYMENT_PAYMENT_STATUS_PAID}" and TF5 status '
                            'to "afsluttet"'
                        )
                    )
                    # NOTE: We just let the logic continue as if successfull
                else:
                    print(f"ProviderPaymentChargeError: {e}")
                    continue
            except Exception as e:
                print(f"Unkown ERROR: {e}")
                continue

            payment.status = settings.PAYMENT_PAYMENT_STATUS_PAID
            payment.save()

            if payment_tf5.status != "afsluttet":
                payment_tf5.status = "afsluttet"
                payment_tf5.save()

            print("  Successfully charged!")

        print("job finished!")
