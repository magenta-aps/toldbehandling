# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import path, reverse
from django.urls.resolvers import URLPattern, URLResolver
from project.api import api
from two_factor.admin import AdminSiteOTPRequired
from two_factor.views import LoginView, QRGeneratorView, SetupCompleteView, SetupView


def empty_favicon(request):
    return HttpResponse(status=204)


class RestAdminSiteOTPRequired(AdminSiteOTPRequired):
    def login(self, request, **kwargs):
        if request.user.is_authenticated and not request.user.is_verified():
            # If the user is logged in but twofactor is not enabled,
            # Send him to the two-factor setup form
            return redirect(reverse("admin_two_factor_setup"))
        else:
            return super().login(request, **kwargs)


class RestAdminSetupView(SetupView):
    success_url = "admin_two_factor_setup_complete"
    qrcode_url = "admin_two_factor_qr"


admin.site.__class__ = RestAdminSiteOTPRequired

urlpatterns: list[URLResolver | URLPattern] = [
    path(
        "api/admin/login",
        LoginView.as_view(),
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
    path("favicon.ico", empty_favicon),
]

urlpatterns += static(
    settings.STATIC_URL,  # type: ignore[arg-type]
    document_root=settings.STATIC_ROOT,  # type: ignore[arg-type]
)
urlpatterns += static(
    settings.MEDIA_URL,  # type: ignore[arg-type]
    document_root=settings.MEDIA_ROOT,  # type: ignore[arg-type]
)
