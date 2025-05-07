# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
from django.urls import include, path
from two_factor.urls import urlpatterns as tf_urls

from told_common import views as common_views

urlpatterns = [
    path("admin/", include("admin.urls")),
    path("admin/twofactor/", include("told_twofactor.urls", namespace="twofactor")),
    path("admin/twofactor/", include(tf_urls)),
    path("admin/login", common_views.LoginView.as_view(), name="login"),
    path("admin/logout", common_views.LogoutView.as_view(url="/admin/"), name="logout"),
]
