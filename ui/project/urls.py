# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import path, include

urlpatterns = [
    path("", include("ui.urls")),
    path("", include("django_mitid_auth.urls", namespace="login")),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
