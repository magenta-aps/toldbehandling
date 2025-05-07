from django.urls import path

from told_common import views as common_views
from told_twofactor import views

# from two_factor import views as twofactor_views


app_name = "told_twofactor"

urlpatterns = [
    path("setup", views.TwoFactorSetupView.as_view(), name="setup"),
    path("login", views.TwofactorLoginView.as_view(), name="login"),
]
