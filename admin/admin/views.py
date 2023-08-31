from typing import Union
from urllib.parse import unquote

from admin.data import Vareafgiftssats
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView, TemplateView
from requests import HTTPError
from told_common.view_mixins import LoginRequiredMixin, HasRestClientMixin

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
            sats_id = varelinje["afgiftssats"]
            varelinje["afgiftssats"] = self.get_sats(sats_id)
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
