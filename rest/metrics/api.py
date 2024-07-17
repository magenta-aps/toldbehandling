# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
# mypy: disable-error-code="call-arg, attr-defined"

import logging
import tempfile

from django.conf import settings
from django.db import connection
from django.http import HttpResponse
from ninja_extra import api_controller, route
from payment.provider_handlers import get_provider_handler

log = logging.getLogger(__name__)


@api_controller(
    "/metrics",
    tags=["metrics"],
)
class MetricsAPI:
    @route.get("/health/storage", url_name="metrics_health_storage")
    def health_storage(self):
        try:
            with tempfile.NamedTemporaryFile(
                dir=settings.MEDIA_ROOT, delete=True
            ) as temp_file:
                temp_file.write(b"Test")
                temp_file.flush()

            return HttpResponse("OK")
        except Exception:
            log.exception("Storage health check failed")
            return HttpResponse("ERROR", status=500)

    @route.get("/health/database", url_name="metrics_health_database")
    def health_database(self):
        try:
            connection.ensure_connection()
            return HttpResponse("OK")
        except Exception:
            log.exception("Database health check failed")
            return HttpResponse("ERROR", status=500)

    @route.get("/health/payment_providers", url_name="metrics_health_payment_providers")
    def health_payment_providers(self):
        providers = [settings.PAYMENT_PROVIDER_NETS, settings.PAYMENT_PROVIDER_BANK]

        for provider in providers:
            try:
                _ = get_provider_handler(provider).ping()
            except Exception:
                log.exception(f"Unable to ping provider: {provider}")
                return HttpResponse("ERROR", status=500)

        return HttpResponse("OK")
