# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import told_common.views as common_views
from django.urls import include, path
from django.views.generic import RedirectView, TemplateView
from django_mitid_auth.saml.views import AccessDeniedView

from ui import views
from betaling import views as betaling_views

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="tf10_list")),
    path("api/<path:path>", common_views.RestView.as_view(), name="rest"),
    path(
        "file/leverandørfaktura/<int:id>",
        common_views.LeverandørFakturaView.as_view(),
        name="leverandørfaktura_view",
    ),
    path(
        "file/fragtbrev/<int:id>",
        common_views.FragtbrevView.as_view(),
        name="fragtbrev_view",
    ),
    path("blanket/tf10/create", views.TF10FormCreateView.as_view(), name="tf10_create"),
    path(
        "blanket/tf10/<int:id>",
        views.TF10FormUpdateView.as_view(),
        name="tf10_edit",
    ),
    path(
        "blanket/tf10/success",
        TemplateView.as_view(template_name="ui/tf10/success.html"),
        name="tf10_blanket_success",
    ),
    path(
        "blanket/tf10",
        views.TF10ListView.as_view(),
        name="tf10_list",
    ),
    path(
        "error/login-timeout/",
        AccessDeniedView.as_view(template_name="ui/error/login_timeout.html"),
        name="login-timeout",
    ),
    path(
        "error/login-repeat/",
        AccessDeniedView.as_view(template_name="ui/error/login_repeat.html"),
        name="login-repeat",
    ),
    # payments
    path("payments/", include("payments.urls")),
    path(
        "betaling/test",
        betaling_views.PaymentTestView.as_view(),
        name="payments-create",
    ),
    path(
        "betaling/detaljer/<int:payment_id>",
        betaling_views.PaymentDetailsView.as_view(),
        name="payments-details",
    ),
]
