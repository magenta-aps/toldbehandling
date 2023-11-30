# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from project.api import api

urlpatterns = [path("admin/", admin.site.urls), path("api/", api.urls)]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
