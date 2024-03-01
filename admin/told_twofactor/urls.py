from django.urls import path

from told_twofactor.views import TwoFactorSetupView

from told_common import views as common_views


app_name = "told_twofactor"

urlpatterns = [
    path("setup", TwoFactorSetupView.as_view(), name="setup"),
    path("base_login", common_views.LoginView.as_view(), name="base_login"),
]
