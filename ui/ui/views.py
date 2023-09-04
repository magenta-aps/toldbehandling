import os
from datetime import date
from typing import Dict, Any
from urllib.parse import unquote

from django.conf import settings
from django.http import JsonResponse, FileResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import FormView
from told_common.view_mixins import (
    FormWithFormsetView,
    LoginRequiredMixin,
    HasRestClientMixin,
)

from ui import forms


class TF10FormView(LoginRequiredMixin, HasRestClientMixin, FormWithFormsetView):
    form_class = forms.TF10Form
    formset_class = forms.TF10VareFormSet
    template_name = "ui/tf10/form.html"

    def get_success_url(self):
        return reverse("tf10_blanket_success")

    def form_valid(self, form, formset):
        afsender_id = self.rest_client.get_or_create_afsender(form.cleaned_data)
        modtager_id = self.rest_client.get_or_create_modtager(form.cleaned_data)
        postforsendelse_id = self.rest_client.create_postforsendelse(form.cleaned_data)
        fragtforsendelse_id = self.rest_client.create_fragtforsendelse(
            form.cleaned_data, self.request.FILES.get("fragtbrev", None)
        )
        anmeldelse_id = self.rest_client.create_anmeldelse(
            self.request,
            form.cleaned_data,
            afsender_id,
            modtager_id,
            postforsendelse_id,
            fragtforsendelse_id,
        )
        self.rest_client.create_varelinjer(
            [subform.cleaned_data for subform in formset], anmeldelse_id
        )
        return super().form_valid(form, formset)

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
        return kwargs

    def get_context_data(self, **context: Dict[str, Any]) -> Dict[str, Any]:
        return super().get_context_data(
            **{**context, "varesatser": self.rest_client.varesatser}
        )


class TF10ListView(LoginRequiredMixin, HasRestClientMixin, FormView):
    template_name = "ui/tf10/list.html"
    form_class = forms.TF10SearchForm
    list_size = 20

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
            if key not in ("json",) and value not in ("", None):
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
            items=items, total=total, search_data=search_data
        )
        if form.cleaned_data["json"]:
            return JsonResponse(
                {
                    "total": total,
                    "items": [
                        {
                            key: self.map_value(item, key)
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

    @staticmethod
    def map_value(item, key):
        if key == "actions":
            html = []
            id = item["id"]
            if item["godkendt"] is None:
                html.append(
                    # TODO: Indsæt den rigtige url (med `reverse()`)
                    #  når vi har en side at henvise til
                    # TODO: Læg dette i template og render den?
                    '<a class="btn btn-primary btn-sm" '
                    f"href=\"something{id}\">{_('Redigér')}</a>"
                )
            return "".join(html)
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
        kwargs["data"] = self.request.GET

        # Will be picked up by TF10SearchForm's constructor
        kwargs["varesatser"] = dict(
            filter(
                lambda pair: pair[1].get("overordnet", None) is None,
                self.rest_client.varesatser.items(),
            )
        )
        return kwargs


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
