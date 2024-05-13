# SPDX-FileCopyrightText: 2024 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from prometheus_client import Counter, Gauge, Histogram

HEALTH_CHECK = Gauge("health_check", "Health status for Toldbehandling")

REQUEST_LATENCY = Histogram(
    "request_latency_seconds",
    "Request latency in seconds",
    ["method", "endpoint"],
)

REQUEST_COUNT = Counter(
    "request_count",
    "Total request count",
    ["method", "endpoint", "http_status"],
)
