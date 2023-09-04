from django.urls import path
from django.views.generic import TemplateView

from told_common.views import (
    LoginView,
    LogoutView,
    RestView,
    FragtbrevView,
    LeverandørFakturaView,
)

from ui import views

urlpatterns = [
    path("login", LoginView.as_view(), name="login"),
    path("logout", LogoutView.as_view(url="/"), name="logout"),
    path("api/<path:path>", RestView.as_view(), name="rest"),
    path(
        "file/leverandørfaktura/<int:id>",
        LeverandørFakturaView.as_view(),
        name="leverandørfaktura_view",
    ),
    path("file/fragtbrev/<int:id>", FragtbrevView.as_view(), name="fragtbrev_view"),
    path("blanket/tf10/create", views.TF10FormView.as_view(), name="tf10_create"),
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
