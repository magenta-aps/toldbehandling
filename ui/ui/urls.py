from django.urls import path
from django.views.generic import TemplateView

from ui import views

urlpatterns = [
    path("login", views.LoginView.as_view(), name="login"),
    path("logout", views.LogoutView.as_view(url="/"), name="logout"),
    path("api/<path:path>", views.RestView.as_view(), name="rest"),
    path("tf10/create", views.TF10FormView.as_view(), name="tf10_create"),
    path(
        "file/leverandørfaktura/<int:id>",
        views.LeverandørFakturaView.as_view(),
        name="leverandørfaktura_view",
    ),
    path(
        "file/fragtbrev/<int:id>", views.FragtbrevView.as_view(), name="fragtbrev_view"
    ),
    path(
        "tf10/success",
        TemplateView.as_view(template_name="ui/tf10/success.html"),
        name="tf10_blanket_success",
    ),
    path(
        "tf10",
        TemplateView.as_view(template_name="ui/tf10/list.html"),
        name="tf10_list",
    ),
]
