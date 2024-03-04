# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from __future__ import annotations

import time
from functools import cached_property
from typing import Any, Dict, Iterable, Optional
from urllib.parse import quote_plus

from django.conf import settings
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
    HttpResponseServerError,
)
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.generic import FormView
from requests import HTTPError
from told_common.data import JwtTokenInfo
from told_common.rest_client import RestClient
from told_common.middleware import RestTokenUserMiddleware




class LoginRequiredMixin:
    def needs_login(self, request):
        if getattr(settings, "LOGIN_PROVIDER_CLASS", None):
            saml_data = request.session.get(settings.LOGIN_SESSION_DATA_KEY)
            if saml_data:
                # Get or create django User, obtain REST token
                user, token = RestClient.login_saml_user(saml_data)
                request.session["user"] = user
                # Save token to session
                token.save(request, save_refresh_token=True)
                RestTokenUserMiddleware.set_user(request)
                return None
            else:
                # Redirect to SAML login
                return redirect(
                    reverse("login:login") + "?back=" + quote_plus(request.path)
                )
        else:
            # Redirect to normal django login
            return redirect(reverse("twofactor:login") + "?back=" + quote_plus(request.path))
            # return redirect(reverse("login") + "?back=" + quote_plus(request.path))

    def login_check(self):
        if not self.request.session.get("access_token") or not self.request.session.get(
            "refresh_token"
        ):
            return self.needs_login(self.request)
        refresh_token_timestamp = self.request.session.get("refresh_token_timestamp")
        if (int(time.time() - float(refresh_token_timestamp))) > 24 * 3600:
            return self.needs_login(self.request)
        return None

    def check(self) -> Optional[HttpResponse]:
        # Underklasser kan overstyre denne metode
        # for at stille yderligere krav til brugeren
        return None

    def dispatch(self, request, *args, **kwargs):
        # self.request = request  klares af superklassen View
        redir = self.login_check() or self.check()
        if redir is not None:
            return redir
        try:
            return super().dispatch(request, *args, **kwargs)
        except HTTPError as e:
            if e.response.status_code == 401:
                # Refresh failed, must re-login
                return self.needs_login(request)
            try:
                content = e.response.json()
            except ValueError:
                content = e.response.content
            return HttpResponseServerError(
                f"Failure in REST API request; "
                f"got http {e.response.status_code} from API. Response: {content}"
            )

    def get_context_data(self, **context):
        return super().get_context_data(**{**context, "user": self.userdata})

    @cached_property
    def userdata(self):
        return self.request.session["user"]


class GroupRequiredMixin(LoginRequiredMixin):
    # Liste af gruppenavne som har tilladelse til at komme ind
    allowed_groups: Iterable[str] = ()

    # Skal stemme overens med de grupper der oprettes i create_groups.py
    PRIVATINDBERETTERE = "PrivatIndberettere"
    ERHVERVINDBERETTERE = "ErhvervIndberettere"
    TOLDMEDARBEJDERE = "Toldmedarbejdere"
    AFSTEMMERE_BOGHOLDERE = "Afstemmere/bogholdere"
    DATAANSVARLIGE = "Dataansvarlige"

    # Som LoginRequiredMixin, men kræver også at brugeren har den rette Permission
    # til at komme ind på admin-sitet
    def check(self) -> Optional[HttpResponse]:
        response = super().check()
        if response:
            return response
        if self.userdata["is_superuser"]:
            return None

        user_groups = set(self.userdata["groups"])
        required_groups = set(self.allowed_groups)
        if required_groups.intersection(user_groups):
            return None

        return TemplateResponse(
            request=self.request,
            template="told_common/access_denied.html",
            context={"missing_groups": self.allowed_groups},
            headers={"Cache-Control": "no-cache"},
            status=403,
        )

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **{
                **kwargs,
                "user_groups": self.userdata["groups"],
            }
        )


class PermissionsRequiredMixin(LoginRequiredMixin):
    # Liste af permissions påkræves for adgang
    required_permissions: Iterable[str] = ()

    # Som LoginRequiredMixin, men kræver også at brugeren har de rette Permissions
    def check(self) -> Optional[HttpResponse]:
        return super().check() or self.check_permissions(self.required_permissions)

    def check_permissions(
        self, required_permissions: Iterable[str]
    ) -> Optional[HttpResponse]:
        if not self.has_permissions(
            request=self.request, required_permissions=required_permissions
        ):
            user_permissions = set(self.userdata["permissions"])
            return TemplateResponse(
                request=self.request,
                status=403,
                template="told_common/access_denied.html",
                context={
                    "missing_permissions": set(required_permissions).difference(
                        user_permissions
                    )
                },
                headers={"Cache-Control": "no-cache"},
            )
        return None

    @classmethod
    def has_permissions(
        cls,
        userdata: dict = None,
        request: HttpRequest = None,
        required_permissions: Iterable[str] = None,
    ) -> bool:
        if userdata is None:
            if request is None:
                raise Exception("Must specify either userdata or request")
            userdata = request.session["user"]
        if userdata["is_superuser"]:
            return True
        if required_permissions is None:
            required_permissions = cls.required_permissions
        required_permissions = set(required_permissions)
        user_permissions = set(userdata["permissions"])
        return required_permissions.issubset(user_permissions)


class HasRestClientMixin:
    def dispatch(self, request, *args, **kwargs):
        self.rest_client = RestClient(token=JwtTokenInfo.load(request))
        response = super().dispatch(request, *args, **kwargs)
        if self.rest_client.token:
            self.rest_client.token.save(request)
        return response


class HasSystemRestClientMixin:
    def dispatch(self, request, *args, **kwargs):
        self.rest_client = RestClient(RestClient.login("system", settings.SYSTEM_USER_PASSWORD))
        response = super().dispatch(request, *args, **kwargs)
        # TODO: Gem token et sted? Ikke oveni den eksisterende sat af HasRestClientMixin
        # TODO: Måske i en class-level cache?
        # if self.rest_client.token:
        #     self.rest_client.token.save(request)
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
        for subform in formset:
            if hasattr(subform, "set_parent_form"):
                subform.set_parent_form(form)
        form.full_clean()
        formset.full_clean()
        if hasattr(form, "clean_with_formset"):
            form.clean_with_formset(formset)
        if form.is_valid() and formset.is_valid():
            return self.form_valid(form, formset)
        else:
            return self.form_invalid(form, formset)


class GetFormView(FormView):
    def get(self, request, *args, **kwargs):
        # Søgeform; viser formularen (med evt. fejl) når den er invalid,
        # og evt. søgeresultater når den er gyldig
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_form_kwargs(self) -> Dict[str, Any]:
        return {**super().get_form_kwargs(), "data": self.request.GET}


class CustomLayoutMixin:
    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **{
                **kwargs,
                "extend_template": self.extend_template,
            }
        )


class TF5Mixin:
    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **{
                **kwargs,
                "hide_api_key_btn": True,
            }
        )
