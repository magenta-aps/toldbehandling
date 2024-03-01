# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
from django.urls import include, path
from two_factor.urls import urlpatterns as tf_urls

urlpatterns = [
    path("admin/", include("admin.urls")),
    path("admin/twofactor/", include("told_twofactor.urls", namespace="twofactor")),
    path("admin/twofactor/", include(tf_urls)),
]
