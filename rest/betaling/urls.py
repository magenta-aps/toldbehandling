# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from betaling import views
from django.urls import include, path

urlpatterns = [
    path("", include("payments.urls")),
    path("details/<str:payment_id>/", views.payment_details, name="payment_details"),
    path("test/", views.payment_test, name="payment_test"),
]
