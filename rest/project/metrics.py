# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from prometheus_client import CollectorRegistry, Gauge


def get_job_metric(job_name: str, registry: CollectorRegistry):
    return Gauge(
        "toldbehandling_job",
        f"Last successful execution time for: {job_name}",
        registry=registry,
    )
