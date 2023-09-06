import os
from urllib.parse import unquote

from django.conf import settings
from django.http import JsonResponse, FileResponse
from django.views import View
from django.views.generic import FormView, RedirectView
from told_common import forms
from told_common.view_mixins import (
    LoginRequiredMixin,
    HasRestClientMixin,
)


class LoginView(FormView):
    form_class = forms.LoginForm
    template_name = "told_common/login.html"

    def get_success_url(self):
        next = self.request.GET.get("next", None)
        if next:
            return next

    def form_valid(self, form):
        response = super().form_valid(form)
        form.token.synchronize(response, synchronize_refresh_token=True)
        return response


class LogoutView(RedirectView):
    pattern_name = "login"

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        return response


class RestView(LoginRequiredMixin, HasRestClientMixin, View):
    def get(self, request, *args, **kwargs) -> JsonResponse:
        data = self.rest_client.get(kwargs["path"], request.GET)
        return JsonResponse(data)


class FileView(LoginRequiredMixin, HasRestClientMixin, View):
    def get(self, request, *args, **kwargs):
        object = self.rest_client.get(
            f"{self.api}/{kwargs['id']}"
        )  # Vil kaste 404 hvis id ikke findes
        # settings.MEDIA_ROOT er monteret i Docker så det deles mellem
        # containerne REST og UI.
        # Derfor kan vi læse filer der er skrevet af den anden container
        path = os.path.join(settings.MEDIA_ROOT, unquote(object[self.key]).lstrip("/"))
        return FileResponse(open(path, "rb"))


class LeverandørFakturaView(FileView):
    api = "afgiftsanmeldelse"
    key = "leverandørfaktura"


class FragtbrevView(FileView):
    api = "fragtforsendelse"
    key = "fragtbrev"
