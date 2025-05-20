# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.urls.resolvers import URLPattern, URLResolver
from project.api import api

urlpatterns: list[URLResolver | URLPattern] = [
    path("api/admin/", admin.site.urls),
    path("api/", api.urls),
]

urlpatterns += static(
    settings.STATIC_URL,  # type: ignore[arg-type]
    document_root=settings.STATIC_ROOT,  # type: ignore[arg-type]
)
urlpatterns += static(
    settings.MEDIA_URL,  # type: ignore[arg-type]
    document_root=settings.MEDIA_ROOT,  # type: ignore[arg-type]
)
