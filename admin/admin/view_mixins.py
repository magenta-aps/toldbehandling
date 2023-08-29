import time

from urllib.parse import quote_plus
from django.http import HttpResponseServerError
from django.shortcuts import redirect
from django.urls import reverse
from requests import HTTPError
from admin.rest_client import JwtTokenInfo, RestClient


class LoginRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.COOKIES.get("access_token") or not request.COOKIES.get(
            "refresh_token"
        ):
            return redirect(reverse("login") + "?next=" + quote_plus(request.path))
        refresh_token_timestamp = request.COOKIES.get("refresh_token_timestamp")
        if (int(time.time() - float(refresh_token_timestamp))) > 24 * 3600:
            return redirect(reverse("login") + "?next=" + quote_plus(request.path))
        try:
            return super().dispatch(request, *args, **kwargs)
        except HTTPError as e:
            if e.response.status_code == 401:
                # Refresh failed, must re-login
                return redirect(reverse("login") + "?next=" + quote_plus(request.path))
            return HttpResponseServerError(
                f"Failure in REST API request; "
                f"got http {e.response.status_code} from API"
            )


class HasRestClientMixin:
    def dispatch(self, request, *args, **kwargs):
        self.rest_client = RestClient(token=JwtTokenInfo.from_cookies(request))
        response = super().dispatch(request, *args, **kwargs)
        self.rest_client.token.synchronize(response)
        return response
