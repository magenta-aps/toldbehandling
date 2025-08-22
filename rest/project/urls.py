# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path, reverse
from django.urls.resolvers import URLPattern, URLResolver
from project.api import api
from two_factor.admin import AdminSiteOTPRequired
from two_factor.urls import urlpatterns as tf_urls


class RestAdminSiteOTPRequired(AdminSiteOTPRequired):
    def login(self, request, **kwargs):
        if request.user.is_authenticated and not request.user.is_verified():
            # If the user is logged in but twofactor is not enabled,
            # Send him to the two-factor setup form
            return redirect(reverse("two_factor:setup"))
        else:
            return super().login(request, **kwargs)


admin.site.__class__ = RestAdminSiteOTPRequired

urlpatterns: list[URLResolver | URLPattern] = [
    path("api/admin/", admin.site.urls),
    path("", include(tf_urls)),
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
