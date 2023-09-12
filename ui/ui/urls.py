import told_common.views as common_views
from django.urls import path
from django.views.generic import TemplateView

from ui import views

urlpatterns = [
    path("login", common_views.LoginView.as_view(), name="login"),
    path("logout", common_views.LogoutView.as_view(url="/"), name="logout"),
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
        common_views.TF10FormUpdateView.as_view(),
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
]
