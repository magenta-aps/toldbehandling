from urllib.parse import quote_plus

from django.http import HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView
from requests import HTTPError
from ui.rest_client import JwtTokenInfo, RestClient


class LoginRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.COOKIES.get("access_token") or not request.COOKIES.get(
            "refresh_token"
        ):
            return redirect(reverse("login") + "?next=" + quote_plus(request.path))
        try:
            return super().dispatch(request, *args, **kwargs)
        except HTTPError as e:
            if e.response.status_code == 401:
                # Refresh failed, must re-login
                return redirect(reverse("login") + "?next=" + quote_plus(request.path))
            return HttpResponseServerError(
                f"Failure in login; got http {e.response.status_code} from API"
            )


class HasRestClientMixin:
    def dispatch(self, request, *args, **kwargs):
        self.rest_client = RestClient(token=JwtTokenInfo.from_cookies(request))
        response = super().dispatch(request, *args, **kwargs)
        self.rest_client.token.synchronize(response)
        return response


class FormWithFormsetView(FormView):
    formset_class = None

    def get_formset(self, formset_class=None):
        if formset_class is None:
            formset_class = self.get_formset_class()
        return formset_class(**self.get_formset_kwargs())

    def get_formset_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = {
            "initial": self.get_initial(),
            "prefix": self.get_prefix(),
        }

        if self.request.method in ("POST", "PUT"):
            kwargs.update(
                {
                    "data": self.request.POST,
                    "files": self.request.FILES,
                }
            )
        return kwargs

    def get_formset_class(self):
        return self.formset_class

    def get_context_data(self, **kwargs):
        if "formset" not in kwargs:
            kwargs["formset"] = self.get_formset()
        return super().get_context_data(**kwargs)

    def form_valid(self, form, formset):
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form, formset):
        return self.render_to_response(
            self.get_context_data(form=form, formset=formset)
        )

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        formset = self.get_formset()
        form.full_clean()
        formset.full_clean()
        if hasattr(form, "clean_with_formset"):
            form.clean_with_formset(formset)
        if form.is_valid() and formset.is_valid():
            return self.form_valid(form, formset)
        else:
            return self.form_invalid(form, formset)
