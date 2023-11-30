# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
from django.urls import include, path

urlpatterns = [
    path("admin/", include("admin.urls")),
]
