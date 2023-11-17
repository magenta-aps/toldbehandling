# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
import dataclasses
import os
from datetime import date
from functools import cached_property
from typing import Any, Dict
from urllib.parse import unquote

from django.conf import settings
from django.http import FileResponse, JsonResponse
from django.template import loader
from django.urls import reverse
from django.views import View
from django.views.generic import FormView, RedirectView
from told_common import forms
from told_common.data import Afgiftsanmeldelse, Forsendelsestype
from told_common.rest_client import RestClient
from told_common.util import JSONEncoder

from told_common.view_mixins import (  # isort: skip
    CustomLayoutMixin,
    FormWithFormsetView,
    HasRestClientMixin,
    LoginRequiredMixin,
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.anmeldelse_id = None

    def get_success_url(self):
        """
        Return to previous page. Highlight the updated form and display a success msg.
        """
        return reverse("tf10_list") + f"?highlight={self.anmeldelse_id}&msg=updated"

    def form_valid(self, form, formset):
        afsender_id = self.rest_client.afsender.get_or_create(
            form.cleaned_data, form.cleaned_data
        )
        modtager_id = self.rest_client.modtager.get_or_create(
            form.cleaned_data, form.cleaned_data
        )

        postforsendelse_id = (
            self.item.postforsendelse.id if self.item.postforsendelse else None
        )
        if postforsendelse_id:
            # Håndterer opdatering og sletning af eksisterende
            postforsendelse_id = self.rest_client.postforsendelse.update(
                postforsendelse_id, form.cleaned_data, self.item.postforsendelse
            )
        else:
            # Håndterer oprettelse af ny
            postforsendelse_id = self.rest_client.postforsendelse.create(
                form.cleaned_data
            )

        fragtforsendelse_id = (
            self.item.fragtforsendelse.id if self.item.fragtforsendelse else None
        )
        if fragtforsendelse_id:
            fragtforsendelse_id = self.rest_client.fragtforsendelse.update(
                fragtforsendelse_id,
                form.cleaned_data,
                self.request.FILES.get("fragtbrev", None),
                self.item.fragtforsendelse,
            )
        else:
            # Håndterer oprettelse af ny
            fragtforsendelse_id = self.rest_client.fragtforsendelse.create(
                form.cleaned_data, self.request.FILES.get("fragtbrev", None)
            )

        self.anmeldelse_id = self.item.id
        self.rest_client.afgiftanmeldelse.update(
            self.anmeldelse_id,
            form.cleaned_data,
            self.request.FILES.get("leverandørfaktura", None),
            afsender_id,
            modtager_id,
            postforsendelse_id,
            fragtforsendelse_id,
            self.item,
            force_write=True,
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
            item.id: {
                f"{key}_id" if key == "vareafgiftssats" else key: value
                for key, value in item.items()
            }
            for item in self.item.varelinjer
        }
        for item in new_items:
            self.rest_client.varelinje.create(item, self.anmeldelse_id)
        for id, item in data_map.items():
            if id in existing_map.keys():
                self.rest_client.varelinje.update(
                    id, item, existing_map[id], self.anmeldelse_id
                )
        for id, item in existing_map.items():
            if id not in data_map:
                self.rest_client.varelinje.delete(id)

        return super().form_valid(form, formset)

    @cached_property
    def toplevel_varesatser(self):
        return dict(
            filter(
                lambda pair: pair[1].get("overordnet", None) is None,
                self.rest_client.varesatser_fra(self.item.dato).items(),
            )
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "leverandørfaktura_required": False,
                "fragtbrev_required": False,
                "varesatser": self.toplevel_varesatser,
            }
        )
        return kwargs

    def get_formset_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_formset_kwargs()
        # The form_kwargs dict is passed as kwargs to subforms in the formset
        if "form_kwargs" not in kwargs:
            kwargs["form_kwargs"] = {}
        # Will be picked up by TF10VareForm's constructor
        kwargs["form_kwargs"]["varesatser"] = self.toplevel_varesatser
        kwargs["initial"] = [dataclasses.asdict(item) for item in self.item.varelinjer]
        return kwargs

    def get_context_data(self, **context: Dict[str, Any]) -> Dict[str, Any]:
        return super().get_context_data(
            **{
                **context,
                "varesatser": self.rest_client.varesatser_fra(self.item.dato),
                "item": self.item,
                "afsender_existing_id": self.item.afsender.id,
                "modtager_existing_id": self.item.modtager.id,
            }
        )

    @cached_property
    def item(self) -> Afgiftsanmeldelse:
        return self.rest_client.afgiftanmeldelse.get(
            self.kwargs["id"],
            full=True,
            include_varelinjer=True,
            include_notater=False,
            include_prismeresponses=False,
        )

    def get_initial(self):
        initial = {}
        item = self.item
        if item:
            for key in ("afsender", "modtager"):
                aktør = getattr(item, key)
                initial.update(
                    {
                        key + "_" + field.name: getattr(aktør, field.name)
                        for field in dataclasses.fields(aktør)
                    }
                )
                initial[key + "_change_existing"] = False
            initial["leverandørfaktura_nummer"] = item.leverandørfaktura_nummer
            initial["indførselstilladelse"] = item.indførselstilladelse
            fragtforsendelse = item.fragtforsendelse
            postforsendelse = item.postforsendelse
            if fragtforsendelse:
                initial["fragttype"] = (
                    "skibsfragt"
                    if fragtforsendelse.forsendelsestype == Forsendelsestype.SKIB
                    else "luftfragt"
                )
                initial["fragtbrevnr"] = fragtforsendelse.fragtbrevsnummer
                initial["forbindelsesnr"] = fragtforsendelse.forbindelsesnr
                initial["afgangsdato"] = fragtforsendelse.afgangsdato
            elif postforsendelse:
                initial["fragttype"] = (
                    "skibspost"
                    if postforsendelse.forsendelsestype == Forsendelsestype.SKIB
                    else "luftpost"
                )
                initial["fragtbrevnr"] = postforsendelse.postforsendelsesnummer
                initial["forbindelsesnr"] = postforsendelse.afsenderbykode
                initial["afgangsdato"] = postforsendelse.afgangsdato
        return initial


class ListView(FormView):
    list_size = 20
    form_class = forms.PaginateForm
    select_template = None

    def get(self, request, *args, **kwargs):
        # Søgeform; viser formularen (med evt. fejl) når den er invalid,
        # og evt. søgeresultater når den er gyldig
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_items(self, search_data: Dict[str, Any]):
        return {"count": 0, "items": []}

    def item_to_json_dict(
        self, item: Dict[str, Any], context: Dict[str, Any], index: int
    ) -> Dict[str, Any]:
        return {**item, "select": item["id"]}

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
        # // = Python floor division
        search_data["page_number"] = (search_data["offset"] // search_data["limit"]) + 1
        response = self.get_items(search_data)
        total = response["count"]
        items = response["items"]
        context = self.get_context_data(
            items=items,
            total=total,
            search_data=search_data,
            actions_template=self.actions_template,
            select_template=self.select_template,
        )
        items = [
            self.item_to_json_dict(item, context, index)
            for index, item in enumerate(items)
        ]
        context["items"] = items
        if form.cleaned_data["json"]:
            return JsonResponse(
                {
                    "total": total,
                    "items": items,
                },
                encoder=JSONEncoder,
            )
        return self.render_to_response(context)

    def form_invalid(self, form):
        if form.cleaned_data["json"]:
            return JsonResponse(
                status=400, data={"count": 0, "items": [], "error": form.errors}
            )
        return super().form_invalid(form)

    def get_form_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_form_kwargs()
        query_dict = self.request.GET.copy()
        kwargs["data"] = query_dict
        return kwargs


class TF10ListView(
    PermissionsRequiredMixin, HasRestClientMixin, CustomLayoutMixin, ListView
):
    required_permissions = (
        "aktør.view_afsender",
        "aktør.view_modtager",
        "forsendelse.view_postforsendelse",
        "forsendelse.view_fragtforsendelse",
        "anmeldelse.view_afgiftsanmeldelse",
        "anmeldelse.view_varelinje",
    )
    select_template = "told_common/tf10/select.html"
    template_name = "told_common/tf10/list.html"
    extend_template = "told_common/layout.html"
    form_class = forms.TF10SearchForm
    list_size = 20

    def get_items(self, search_data: Dict[str, Any]):
        # return self.rest_client.get("afgiftsanmeldelse/full", search_data)
        count, items = self.rest_client.afgiftanmeldelse.list(full=True, **search_data)
        return {"count": count, "items": items}

    def get_context_data(self, **context: Dict[str, Any]) -> Dict[str, Any]:
        return super().get_context_data(
            **{
                **context,
                "title": "Mine afgiftsanmeldelser",
            }
        )

    def item_to_json_dict(
        self, item: Dict[str, Any], context: Dict[str, Any], index: int
    ) -> Dict[str, Any]:
        return {
            key: self.map_value(item, key, context)
            for key in (
                "select",
                "id",
                "dato",
                "afsender",
                "modtager",
                "godkendt",
                "actions",
            )
        }

    def map_value(self, item, key, context):
        if key == "actions":
            return loader.render_to_string(
                self.actions_template,
                {"item": item, **context},
                self.request,
            )
        if key == "select":
            return loader.render_to_string(
                self.select_template,
                {"item": item, **context},
                self.request,
            )
        value = getattr(item, key)
        return value

    def get_form_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_form_kwargs()
        query_dict = self.request.GET.copy()

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
