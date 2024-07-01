# SPDX-FileCopyrightText: 2024 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from prometheus_client import CollectorRegistry, Gauge

JOB_EXEC_TIME_REGISTRY = CollectorRegistry()
JOB_EXEC_TIME = Gauge(
    "groenland_job",
    "Latest execution time",
    registry=JOB_EXEC_TIME_REGISTRY,
)
