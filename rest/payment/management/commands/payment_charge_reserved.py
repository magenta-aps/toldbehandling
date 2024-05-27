from django.core.management.base import BaseCommand
from metrics.job import JOB_EXEC_TIME, JOB_EXEC_TIME_REGISTRY
from payment.exceptions import ProviderPaymentNotFound
from payment.models import Payment
from payment.provider_handlers import get_provider_handler
from project import settings
from prometheus_client import push_to_gateway


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
            except Exception as e:
                print(f"ERROR: {e}")
                continue

            payment.status = "paid"
            payment.save()

            print("  Successfully charged!")

        # Push a metric to prometheus
        try:
            JOB_EXEC_TIME.set_to_current_time()
            push_to_gateway(
                settings.PROMETHEUS_PUSHGATEWAY_HOST,
                job="payment_charge_reserved",
                registry=JOB_EXEC_TIME_REGISTRY,
            )
        except Exception as e:
            print(
                (
                    "Unable to push metrics to "
                    f"prometheus-pushgateway: {settings.PROMETHEUS_PUSHGATEWAY_HOST}"
                )
            )
            raise e

        print("job finished!")
