# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from django.urls import path
from django.views.generic.base import RedirectView
from told_common import views as common_views

from admin import views

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
        "afgiftstabel/create",
        views.AfgiftstabelCreateView.as_view(),
        name="afgiftstabel_create",
    ),
    path(
        "afgiftstabel/<int:id>/<str:format>",
        views.AfgiftstabelDownloadView.as_view(),
        name="afgiftstabel_download",
    ),
    path("blanket/tf10/create", views.TF10FormCreateView.as_view(), name="tf10_create"),
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
    path("statistik", views.StatistikView.as_view(), name="statistik"),
]
