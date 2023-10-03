# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import os
from datetime import date
from functools import cached_property
from typing import Dict, Any
from urllib.parse import unquote

from django.conf import settings
from django.http import JsonResponse, FileResponse
from django.template import loader
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import FormView, RedirectView
from told_common import forms
from told_common.rest_client import RestClient
from told_common.view_mixins import (
    FormWithFormsetView,
    LoginRequiredMixin,
    HasRestClientMixin,
    CustomLayoutMixin,
    PermissionsRequiredMixin,
)


class LoginView(FormView):
    form_class = forms.LoginForm
    template_name = "told_common/login.html"

    def get_success_url(self):
        next = self.request.GET.get("back", None)
        if next:
            return next

    def form_valid(self, form):
        form.token.save(self.request, save_refresh_token=True)
        userdata = RestClient(form.token).get("user")
        self.request.session["user"] = userdata
        return super().form_valid(form)


class LogoutView(RedirectView):
    pattern_name = "login"

    def get(self, request, *args, **kwargs):
        for key in ("access_token", "refresh_token", "user"):
            if key in request.session:
                del request.session[key]
        return super().get(request, *args, **kwargs)


class RestView(LoginRequiredMixin, HasRestClientMixin, View):
    def get(self, request, *args, **kwargs) -> JsonResponse:
        data = self.rest_client.get(kwargs["path"], request.GET)
        return JsonResponse(data)


class FileView(LoginRequiredMixin, HasRestClientMixin, View):
    def get(self, request, *args, **kwargs):
        # Vil kaste 404 hvis id ikke findes
        object = self.rest_client.get(f"{self.api}/{kwargs['id']}")
        # settings.MEDIA_ROOT er monteret i Docker så det deles mellem
        # containerne REST og UI.
        # Derfor kan vi læse filer der er skrevet af den anden container
        path = os.path.join(settings.MEDIA_ROOT, unquote(object[self.key]).lstrip("/"))
        return FileResponse(open(path, "rb"))


class LeverandørFakturaView(PermissionsRequiredMixin, FileView):
    required_permissions = ("anmeldelse.view_afgiftsanmeldelse",)
    api = "afgiftsanmeldelse"
    key = "leverandørfaktura"


class FragtbrevView(PermissionsRequiredMixin, FileView):
    required_permissions = ("forsendelse.view_fragtforsendelse",)
    api = "fragtforsendelse"
    key = "fragtbrev"


class TF10FormUpdateView(
    PermissionsRequiredMixin, HasRestClientMixin, CustomLayoutMixin, FormWithFormsetView
):
    required_permissions = (
        "aktør.view_afsender",
        "aktør.view_modtager",
        "forsendelse.view_postforsendelse",
        "forsendelse.view_fragtforsendelse",
        "anmeldelse.view_afgiftsanmeldelse",
        "anmeldelse.view_varelinje",
        "aktør.add_afsender",
        "aktør.add_modtager",
        "forsendelse.add_postforsendelse",
        "forsendelse.add_fragtforsendelse",
        "anmeldelse.add_afgiftsanmeldelse",
        "anmeldelse.add_varelinje",
    )
    form_class = forms.TF10Form
    formset_class = forms.TF10VareFormSet
    template_name = "told_common/tf10/form.html"
    extend_template = "told_common/layout.html"

    def get_success_url(self):
        return reverse("tf10_list")

    def form_valid(self, form, formset):
        afsender_id = self.rest_client.afsender.get_or_create(form.cleaned_data)
        modtager_id = self.rest_client.modtager.get_or_create(form.cleaned_data)

        postforsendelse_id = (
            self.item["postforsendelse"]["id"] if self.item["postforsendelse"] else None
        )
        if postforsendelse_id:
            # Håndterer opdatering og sletning af eksisterende
            postforsendelse_id = self.rest_client.postforsendelse.update(
                postforsendelse_id, form.cleaned_data, self.item["postforsendelse"]
            )
        else:
            # Håndterer oprettelse af ny
            postforsendelse_id = self.rest_client.postforsendelse.create(
                form.cleaned_data
            )

        fragtforsendelse_id = (
            self.item["fragtforsendelse"]["id"]
            if self.item["fragtforsendelse"]
            else None
        )
        if fragtforsendelse_id:
            fragtforsendelse_id = self.rest_client.fragtforsendelse.update(
                fragtforsendelse_id,
                form.cleaned_data,
                self.request.FILES.get("fragtbrev", None),
                self.item["fragtforsendelse"],
            )
        else:
            # Håndterer oprettelse af ny
            fragtforsendelse_id = self.rest_client.fragtforsendelse.create(
                form.cleaned_data, self.request.FILES.get("fragtbrev", None)
            )

        anmeldelse_id = self.item["id"]
        self.rest_client.afgiftanmeldelse.update(
            anmeldelse_id,
            form.cleaned_data,
            self.request.FILES.get("leverandørfaktura", None),
            afsender_id,
            modtager_id,
            postforsendelse_id,
            fragtforsendelse_id,
            self.item,
        )

        data_map = {
            subform.cleaned_data["id"]: subform.cleaned_data
            for subform in formset
            if subform.cleaned_data["id"]
        }
        new_items = [
            subform.cleaned_data
            for subform in formset
            if not subform.cleaned_data["id"]
        ]
        existing_map = {
            item["id"]: {
                f"{key}_id" if key == "vareafgiftssats" else key: value
                for key, value in item.items()
            }
            for item in self.varelinjer
        }
        for item in new_items:
            self.rest_client.varelinje.create(item, anmeldelse_id)
        for id, item in data_map.items():
            if id in existing_map.keys():
                self.rest_client.varelinje.update(
                    id, item, existing_map[id], anmeldelse_id
                )
        for id, item in existing_map.items():
            if id not in data_map:
                self.rest_client.varelinje.delete(id)

        return super().form_valid(form, formset)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {"leverandørfaktura_required": False, "fragtbrev_required": False}
        )
        return kwargs

    def get_formset_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_formset_kwargs()
        # The form_kwargs dict is passed as kwargs to subforms in the formset
        if "form_kwargs" not in kwargs:
            kwargs["form_kwargs"] = {}
        # Will be picked up by TF10VareForm's constructor
        kwargs["form_kwargs"]["varesatser"] = dict(
            filter(
                lambda pair: pair[1].get("overordnet", None) is None,
                self.rest_client.varesatser.items(),
            )
        )
        kwargs["initial"] = self.varelinjer
        return kwargs

    def get_context_data(self, **context: Dict[str, Any]) -> Dict[str, Any]:
        return super().get_context_data(
            **{
                **context,
                "varesatser": self.rest_client.varesatser,
                "item": self.item,
            }
        )

    @cached_property
    def item(self):
        return self.rest_client.get(f"afgiftsanmeldelse/{self.kwargs['id']}/full")

    @cached_property
    def varelinjer(self):
        response = self.rest_client.get(
            "varelinje", {"afgiftsanmeldelse": self.kwargs["id"]}
        )
        return [
            {
                "id": item["id"],
                "vareafgiftssats": item["vareafgiftssats"],
                "mængde": item["mængde"],
                "antal": item["antal"],
                "fakturabeløb": item["fakturabeløb"],
            }
            for item in response["items"]
        ]

    def get_initial(self):
        initial = {}
        item = self.item
        if item:
            for key in ("afsender", "modtager"):
                initial.update(
                    {key + "_" + subkey: item[key][subkey] for subkey in item[key]}
                )
            initial["leverandørfaktura_nummer"] = item["leverandørfaktura_nummer"]
            fragtforsendelse = item.get("fragtforsendelse", None)
            postforsendelse = item.get("postforsendelse", None)
            if fragtforsendelse:
                initial["fragttype"] = (
                    "skibsfragt"
                    if fragtforsendelse["forsendelsestype"] == "S"
                    else "luftfragt"
                )
                initial["fragtbrevnr"] = fragtforsendelse["fragtbrevsnummer"]
                initial["forbindelsesnr"] = fragtforsendelse["forbindelsesnr"]
            elif postforsendelse:
                initial["fragttype"] = (
                    "skibspost"
                    if postforsendelse["forsendelsestype"] == "S"
                    else "luftpost"
                )
                initial["fragtbrevnr"] = postforsendelse["postforsendelsesnummer"]
                initial["forbindelsesnr"] = postforsendelse["afsenderbykode"]
        return initial


class TF10ListView(
    PermissionsRequiredMixin, HasRestClientMixin, CustomLayoutMixin, FormView
):
    required_permissions = (
        "aktør.view_afsender",
        "aktør.view_modtager",
        "forsendelse.view_postforsendelse",
        "forsendelse.view_fragtforsendelse",
        "anmeldelse.view_afgiftsanmeldelse",
        "anmeldelse.view_varelinje",
    )
    template_name = "told_common/tf10/list.html"
    extend_template = "told_common/layout.html"
    form_class = forms.TF10SearchForm
    list_size = 20

    def get_context_data(self, **context: Dict[str, Any]) -> Dict[str, Any]:
        return super().get_context_data(
            **{
                **context,
                "title": "Mine afgiftsanmeldelser",
            }
        )

    def get(self, request, *args, **kwargs):
        # Søgeform; viser formularen (med evt. fejl) når den er invalid,
        # og evt. søgeresultater når den er gyldig
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        search_data = {"offset": 0, "limit": self.list_size}
        for key, value in form.cleaned_data.items():
            if key not in ("json",) and value not in ("", None, "explicitly_none"):
                if type(value) is date:
                    value = value.isoformat()
                elif key in ("offset", "limit"):
                    value = int(value)
                search_data[key] = value
        if search_data["offset"] < 0:
            search_data["offset"] = 0
        if search_data["limit"] < 1:
            search_data["limit"] = 1
        response = self.rest_client.get("afgiftsanmeldelse/full", search_data)
        total = response["count"]
        items = response["items"]
        context = self.get_context_data(
            items=items,
            total=total,
            search_data=search_data,
            actions_template=self.actions_template,
        )
        if form.cleaned_data["json"]:
            return JsonResponse(
                {
                    "total": total,
                    "items": [
                        {
                            key: self.map_value(item, key, context)
                            for key in (
                                "id",
                                "dato",
                                "afsender",
                                "modtager",
                                "godkendt",
                                "actions",
                            )
                        }
                        for item in items
                    ],
                }
            )
        return self.render_to_response(context)

    def form_invalid(self, form):
        if form.cleaned_data["json"]:
            return JsonResponse(
                status=400, data={"count": 0, "items": [], "error": form.errors}
            )
        return super().form_invalid(form)

    def map_value(self, item, key, context):
        if key == "actions":
            return loader.render_to_string(
                self.actions_template,
                {"item": item, **context},
                self.request,
            )
        value = item[key]
        if key in ("afsender", "modtager"):
            return value["navn"]
        if key == "godkendt":
            if value is True:
                return _("Godkendt")
            elif value is False:
                return _("Afvist")
            else:
                return _("Ny")
        return value

    def get_form_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_form_kwargs()
        query_dict = self.request.POST.copy()

        if query_dict.get("godkendt", "") == "explicitly_none":
            query_dict["godkendt_is_null"] = "True"
        kwargs["data"] = query_dict

        # Will be picked up by TF10SearchForm's constructor
        kwargs["varesatser"] = dict(
            filter(
                lambda pair: pair[1].get("overordnet", None) is None,
                self.rest_client.varesatser.items(),
            )
        )
        kwargs["afsendere"] = {
            item[1]["id"]: item[1] for item in self.rest_client.afsendere.items()
        }
        kwargs["modtagere"] = {
            item[1]["id"]: item[1] for item in self.rest_client.modtagere.items()
        }
        return kwargs
