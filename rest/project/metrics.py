# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from prometheus_client import CollectorRegistry, Counter, Gauge

# Payment metrics


metric_payment_provider_payments_created = Counter(
    "toldbehandling_payments_created_total",
    "Total number of provider payments created",
)

metric_payment_provider_payments_reserved = Counter(
    "toldbehandling_payments_reserved_total",
    "Total number of provider payments reserved",
)


# Job metrics


def get_job_metric(job_name: str, registry: CollectorRegistry):
    return Gauge(
        "toldbehandling_job",
        f"Last successful execution time for: {job_name}",
        registry=registry,
    )
