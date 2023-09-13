from typing import Union
from urllib.parse import unquote

from admin.data import Vareafgiftssats
from django.http import Http404, JsonResponse
from django.shortcuts import redirect
from django.template import loader
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, TemplateView
from requests import HTTPError
from told_common import views as common_views
from told_common.view_mixins import LoginRequiredMixin, HasRestClientMixin, GetFormView

from admin import forms


class IndexView(LoginRequiredMixin, HasRestClientMixin, TemplateView):
    template_name = "admin/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        tf10_forms = [
            {
                "date": "2023-01-01 08:00",
                "status": "open",
                "id": 1,
            },
            {
                "date": "2023-01-01 08:00",
                "status": "needs review",
                "id": 2,
            },
            {
                "date": "2023-01-01 08:00",
                "status": "closed",
                "id": 3,
            },
        ]

        context["tf10_forms"] = tf10_forms
        return context


class TF10View(LoginRequiredMixin, HasRestClientMixin, FormView):
    template_name = "admin/blanket/tf10/view.html"
    form_class = forms.TF10GodkendForm

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **{
                **kwargs,
                "object": self.get_object(),
            }
        )

    def form_valid(self, form):
        godkendt = form.cleaned_data["godkendt"]
        anmeldelse_id = self.kwargs["id"]
        try:
            self.rest_client.patch(
                f"afgiftsanmeldelse/{anmeldelse_id}", {"godkendt": godkendt}
            )
            return redirect(reverse("tf10_view", kwargs={"id": anmeldelse_id}))
        except HTTPError as e:
            if e.response.status_code == 404:
                raise Http404("Afgiftsanmeldelse findes ikke")
            raise

    def get_object(self):
        try:
            anmeldelse = self.get_data("afgiftsanmeldelse", self.kwargs["id"])
        except HTTPError as e:
            if e.response.status_code == 404:
                raise Http404("Afgiftsanmeldelse findes ikke")
            raise
        for key in ("afsender", "modtager", "fragtforsendelse", "postforsendelse"):
            if anmeldelse[key] is not None:
                anmeldelse[key] = self.get_data(key, anmeldelse[key])
        anmeldelse["varelinjer"] = self.rest_client.get(
            "varelinje", {"afgiftsanmeldelse": anmeldelse["id"]}
        )["items"]
        for varelinje in anmeldelse["varelinjer"]:
            sats_id = varelinje["vareafgiftssats"]
            varelinje["vareafgiftssats"] = self.get_sats(sats_id)
        return anmeldelse

    def get_data(self, api, id) -> Union[dict, None]:
        # Filfelter som indeholder en sti der er urlquotet af Django Ninja
        unquote_keys = (
            ("afgiftsanmeldelse", "leverandørfaktura"),
            ("fragtforsendelse", "fragtbrev"),
        )
        data = self.rest_client.get(f"{api}/{id}")
        for key_api, key_field in unquote_keys:
            if api == key_api and data.get(key_field, None):
                data[key_field] = unquote(data[key_field])
        return data

    _satser = {}

    def get_sats(self, sats_id: int) -> Vareafgiftssats:
        if sats_id not in self._satser:
            sats = Vareafgiftssats.from_dict(self.get_data("vareafgiftssats", sats_id))
            if sats.enhed == Vareafgiftssats.Enhed.SAMMENSAT:
                response = self.rest_client.get(
                    "vareafgiftssats", {"overordnet": sats_id}
                )
                if response["count"] > 0:
                    sats.subsatser = []
                    for subsats in response["items"]:
                        subsats = Vareafgiftssats.from_dict(subsats)
                        if subsats.id not in self._satser:
                            self._satser[subsats.id] = subsats
                        sats.subsatser.append(subsats)
            self._satser[sats_id] = sats
        return self._satser[sats_id]


class TF10ListView(common_views.TF10ListView):
    actions_template = "admin/blanket/tf10/link.html"
    extend_template = "admin/admin_layout.html"

    def get_context_data(self, **context):
        return super().get_context_data(**{**context, "can_create": False})


class TF10FormUpdateView(common_views.TF10FormUpdateView):
    extend_template = "admin/admin_layout.html"

    def get_success_url(self):
        return reverse("tf10_view", kwargs={"id": self.kwargs["id"]})


class AfgiftstabelListView(LoginRequiredMixin, HasRestClientMixin, GetFormView):
    template_name = "admin/afgiftstabel/list.html"
    form_class = forms.AfgiftstabelSearchForm
    actions_template = "admin/afgiftstabel/handlinger.html"
    list_size = 20

    def get_context_data(self, **context):
        return super().get_context_data(
            **{**context, "actions_template": self.actions_template}
        )

    def form_valid(self, form):
        search_data = {"offset": 0, "limit": self.list_size}
        for key, value in form.cleaned_data.items():
            if key not in ("json",) and value not in ("", None):
                if key in ("offset", "limit"):
                    value = int(value)
                search_data[key] = value
        if search_data["offset"] < 0:
            search_data["offset"] = 0
        if search_data["limit"] < 1:
            search_data["limit"] = 1
        response = self.rest_client.get("afgiftstabel", search_data)
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
                                "gyldig_fra",
                                "gyldig_til",
                                "kladde",
                                "actions",
                            )
                        }
                        for item in items
                    ],
                }
            )
        return self.render_to_response(context)

    def map_value(self, item, key):
        if key == "actions":
            return loader.render_to_string(
                self.actions_template, {"item": item}, self.request
            )
        value = item[key]
        if type(value) is bool:
            value = _("ja") if value else _("nej")
        if value is None:
            value = ""
        return value
