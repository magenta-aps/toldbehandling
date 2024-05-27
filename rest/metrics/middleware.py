# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import time

from metrics.project import REQUEST_COUNT, REQUEST_LATENCY


class MetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        request_latency = time.time() - start_time

        REQUEST_LATENCY.labels(method=request.method, endpoint=request.path).observe(
            request_latency
        )

        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.path,
            http_status=response.status_code,
        ).inc()

        return response
