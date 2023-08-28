from django.urls import path
from django.views.generic import TemplateView

from admin import views

urlpatterns = [
    path("login", views.LoginView.as_view(), name="login"),
    path("logout", views.LogoutView.as_view(url="/"), name="logout"),
    path("api/<path:path>", views.RestView.as_view(), name="rest"),
    path("index", views.IndexView.as_view(), name="index"),
    path("tf10/<int:id>", views.TF10View.as_view(), name="tf10_view"),
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
        TemplateView.as_view(template_name="admin/tf10/success.html"),
        name="tf10_blanket_success",
    ),
]
