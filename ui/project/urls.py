# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from django.conf import settings
from django.urls import include, path

urlpatterns = [
    path("", include("ui.urls")),
    path("", include("django_mitid_auth.urls", namespace=settings.LOGIN_NAMESPACE)),
]

if settings.MITID_TEST_ENABLED:
    urlpatterns.append(
        path("mitid_test/", include("mitid_test.urls", namespace="mitid_test"))
    )
