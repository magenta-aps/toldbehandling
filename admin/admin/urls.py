from django.urls import path
from django.views.generic import TemplateView

from admin import views

urlpatterns = [
    path("login", views.LoginView.as_view(), name="login"),
    path("logout", views.LogoutView.as_view(url="/"), name="logout"),
    path("api/<path:path>", views.RestView.as_view(), name="rest"),
    path("index", views.IndexView.as_view(), name="index"),
    path(
        "file/leverandørfaktura/<int:id>",
        views.LeverandørFakturaView.as_view(),
        name="leverandørfaktura_view",
    ),
    path(
        "file/fragtbrev/<int:id>", views.FragtbrevView.as_view(), name="fragtbrev_view"
    ),
    path(
        "afgiftstabel",
        TemplateView.as_view(template_name="admin/afgiftstabel/list.html"),
        name="afgiftstabel_list",
    ),
    path(
        "afgiftstabel/1",
        TemplateView.as_view(template_name="admin/afgiftstabel/view.html"),
        name="afgiftstabel_view",
    ),
    path(
        "afgiftstabel/create",
        TemplateView.as_view(template_name="admin/afgiftstabel/form.html"),
        name="afgiftstabel_create",
    ),
    path(
        "blanketter/tf10",
        TemplateView.as_view(template_name="admin/blanket/tf10/list.html"),
        name="tf10_list",
    ),
    path("blanketter/tf10/<int:id>", views.TF10View.as_view(), name="tf10_view"),
    path(
        "blanketter/tf10/ubehandlede",
        TemplateView.as_view(template_name="admin/blanket/tf10/list_ubehandlede.html"),
        name="tf10_list_ubehandlede",
    ),
    path(
        "blanketter/tf10/behandlede",
        TemplateView.as_view(template_name="admin/blanket/tf10/list_behandlede.html"),
        name="tf10_list_behandlede",
    ),
    path(
        "blanketter/tf10/afsluttede",
        TemplateView.as_view(template_name="admin/blanket/tf10/list_afsluttede.html"),
        name="tf10_list_afsluttede",
    ),
    path(
        "faktura",
        TemplateView.as_view(template_name="admin/faktura/form.html"),
        name="faktura_create",
    ),
]
