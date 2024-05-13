# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
# mypy: disable-error-code="call-arg, attr-defined"

from django.http import HttpResponse
from ninja_extra import api_controller, route
from ninja_jwt.authentication import JWTAuth
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest


@api_controller(
    "/metrics",
    tags=["metrics"],
)
class MetricsAPI:
    @route.get("", url_name="metrics_prometheus")
    def get_all(self):
        return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)

    @route.get("/health", auth=JWTAuth(), url_name="metrics_health")
    def health(self):
        # TODO: Check DB connection
        # TODO: Check external services

        return HttpResponse("OK")
