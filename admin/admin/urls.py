# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from django.urls import path
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
from told_common import views as common_views

from admin import views

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="tf10_list")),
    path("login", common_views.LoginView.as_view(), name="login"),
    path("logout", common_views.LogoutView.as_view(url="/admin/"), name="logout"),
    path("api/<path:path>", common_views.RestView.as_view(), name="rest"),
    path("index", views.IndexView.as_view(), name="index"),
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
    path(
        "afgiftstabel",
        views.AfgiftstabelListView.as_view(),
        name="afgiftstabel_list",
    ),
    path(
        "afgiftstabel/<int:id>",
        views.AfgiftstabelDetailView.as_view(),
        name="afgiftstabel_view",
    ),
    path(
        "afgiftstabel/2",
        TemplateView.as_view(template_name="admin/afgiftstabel/view_kladde.html"),
        name="afgiftstabel_view_kladde",
    ),
    path(
        "afgiftstabel/create",
        views.AfgiftstabelCreateView.as_view(),
        name="afgiftstabel_create",
    ),
    path(
        "afgiftstabel/activate",
        TemplateView.as_view(template_name="admin/afgiftstabel/aktiver.html"),
        name="afgiftstabel_activate",
    ),
    path(
        "afgiftstabel/<int:id>/<str:format>",
        views.AfgiftstabelDownloadView.as_view(),
        name="afgiftstabel_download",
    ),
    path(
        "blanket/tf10",
        views.TF10ListView.as_view(),
        name="tf10_list",
    ),
    path("blanket/tf10/<int:id>", views.TF10View.as_view(), name="tf10_view"),
    path(
        "blanket/tf10/<int:id>/edit",
        views.TF10FormUpdateView.as_view(),
        name="tf10_edit",
    ),
    path(
        "blanket/tf10/<int:id>/history",
        views.TF10HistoryListView.as_view(),
        name="tf10_history",
    ),
    path(
        "blanket/tf10/<int:id>/history/<int:index>",
        views.TF10HistoryDetailView.as_view(),
        name="tf10_history_view",
    ),
    path(
        "blanket/tf10/edit",
        views.TF10EditMultipleView.as_view(),
        name="tf10_edit_multiple",
    ),
]
