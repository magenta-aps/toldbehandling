# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect
from django.urls import path
from django.urls.resolvers import URLPattern, URLResolver
from project.api import api
from two_factor.admin import AdminSiteOTPRequired
from two_factor.views import LoginView, QRGeneratorView, SetupCompleteView, SetupView


class RestAdminSetupView(SetupView):
    success_url = "admin_two_factor_setup_complete"
    qrcode_url = "admin_two_factor_qr"


class RestAdminLoginView(LoginView):

    if not settings.REQUIRE_2FA:  # type: ignore
        form_list = (("auth", AuthenticationForm),)

    def done(self, form_list, **kwargs):
        """
        Login the user and redirect to the desired page.
        """

        login(self.request, self.get_user())
        device = getattr(self.get_user(), "otp_device", None)

        # If the user does not have a device.
        if not device and settings.REQUIRE_2FA:  # type: ignore
            return redirect("admin_two_factor_setup")
        else:
            return super().done(form_list, **kwargs)


if settings.REQUIRE_2FA:  # type: ignore
    admin.site.__class__ = AdminSiteOTPRequired

urlpatterns: list[URLResolver | URLPattern] = [
    path(
        "api/admin/login",
        RestAdminLoginView.as_view(),
        name="django_admin_login",
    ),
    path(
        "api/admin/two_factor/setup",
        RestAdminSetupView.as_view(),
        name="admin_two_factor_setup",
    ),
    path(
        "api/admin/two_factor/setup_complete",
        SetupCompleteView.as_view(),
        name="admin_two_factor_setup_complete",
    ),
    path(
        "api/admin/two_factor/qr",
        QRGeneratorView.as_view(),
        name="admin_two_factor_qr",
    ),
    path("api/admin/", admin.site.urls),
    path("api/", api.urls),
]

urlpatterns += static(
    settings.STATIC_URL,  # type: ignore[arg-type]
    document_root=settings.STATIC_ROOT,  # type: ignore[arg-type]
)
urlpatterns += static(
    settings.MEDIA_URL,  # type: ignore[arg-type]
    document_root=settings.MEDIA_ROOT,  # type: ignore[arg-type]
)
