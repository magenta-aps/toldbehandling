from django.urls import path

from told_twofactor import views

from told_common import views as common_views
# from two_factor import views as twofactor_views


app_name = "told_twofactor"

urlpatterns = [
    path("setup", views.TwoFactorSetupView.as_view(), name="setup"),
    path("login", views.TwofactorLoginView.as_view(), name="login"),
    path("base_login", common_views.LoginView.as_view(), name="base_login"),

    # path(
    #     'account/two_factor/setup/',
    #     twofactor_views.SetupView.as_view(),
    #     name='setup',
    # ),
    # path(
    #     'account/two_factor/qrcode/',
    #     twofactor_views.QRGeneratorView.as_view(),
    #     name='qr',
    # ),
    # path(
    #     'account/two_factor/setup/complete/',
    #     twofactor_views.SetupCompleteView.as_view(),
    #     name='setup_complete',
    # ),
]
