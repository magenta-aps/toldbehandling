# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import told_common.views as common_views
from django.conf import settings
from django.urls import include, path
from django.urls.resolvers import URLPattern, URLResolver
from django.views.generic import TemplateView
from django_mitid_auth.saml.views import AccessDeniedView

from ui import views
from ui.views import IndexView

urlpatterns: list[URLResolver | URLPattern] = [
    path("", IndexView.as_view()),
    path("rest/<path:path>", common_views.RestView.as_view(), name="rest"),
    path("user/sync", common_views.SyncSessionView.as_view(), name="sync_session"),
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
    path("blanket/tf10/<int:id>", views.TF10View.as_view(), name="tf10_view"),
    path(
        "blanket/tf10/<int:id>/edit",
        views.TF10FormUpdateView.as_view(),
        name="tf10_edit",
    ),
    path(
        "blanket/tf10",
        views.TF10ListView.as_view(),
        name="tf10_list",
    ),
    path(
        "blanket/tf10/<int:id>/leverandørfaktura",
        views.TF10LeverandørFakturaView.as_view(),
        name="tf10_leverandørfaktura",
    ),
    path(
        "blanket/tf10/<int:id>/delete",
        views.TF10DeleteView.as_view(),
        name="tf10_delete",
    ),
]
if settings.TF5_ENABLED:  # type: ignore
    urlpatterns += [
        path(
            "blanket/tf5/create",
            views.TF5FormCreateView.as_view(),
            name="tf5_create",
        ),
        path("blanket/tf5", views.TF5ListView.as_view(), name="tf5_list"),
        path(
            "blanket/tf5/<int:id>",
            views.TF5View.as_view(),
            name="tf5_view",
        ),
        path(
            "blanket/tf5/<int:id>/edit",
            views.TF5UpdateView.as_view(),
            name="tf5_edit",
        ),
        path(
            "blanket/tf5/<int:id>/leverandørfaktura",
            views.TF5LeverandørFakturaView.as_view(),
            name="tf5_leverandørfaktura",
        ),
        path(
            "blanket/tf5/<int:id>/tilladelse",
            views.TF5TilladelseView.as_view(),
            name="tf5_tilladelse",
        ),
        path(
            "payment/checkout/<int:id>",
            views.TF5PaymentCheckoutView.as_view(),
            name="tf5_payment_checkout",
        ),
        path(
            "payment/details/<int:id>",
            views.TF5PaymentDetailsView.as_view(),
            name="tf5_payment_details",
        ),
        path(
            "payment/refresh/<int:id>",
            views.TF5PaymentRefreshView.as_view(),
            name="tf5_payment_refresh",
        ),
    ]
urlpatterns += [
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
    path(
        "error/login-login_assurance/",
        AccessDeniedView.as_view(template_name="ui/error/login_assurance.html"),
        name="login-assurance-level",
    ),
    path(
        "logged-out/",
        TemplateView.as_view(template_name="ui/loggedout.html"),
        name="logged-out",
    ),
    path("i18n/", include("django.conf.urls.i18n")),
]
