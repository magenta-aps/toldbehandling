import csv
from collections import defaultdict
from datetime import date
from functools import cached_property
from typing import Union, Iterable, List
from urllib.parse import unquote

from admin.data import Afgiftstabel
from admin.data import Vareafgiftssats
from django.http import Http404, JsonResponse, HttpResponseBadRequest, HttpResponse
from django.shortcuts import redirect
from django.template import loader
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import FormView, TemplateView
from openpyxl import Workbook
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
            sats.populate_subs(self.get_subsatser)
            self._satser[sats_id] = sats
        return self._satser[sats_id]

    def get_subsatser(self, parent_id: int) -> List[Vareafgiftssats]:
        response = self.rest_client.get("vareafgiftssats", {"overordnet": parent_id})
        subsatser = []
        for subsats in response["items"]:
            subsats = Vareafgiftssats.from_dict(subsats)
            if subsats.id not in self._satser:
                self._satser[subsats.id] = subsats
            subsatser.append(subsats)
        return subsatser


class TF10ListView(common_views.TF10ListView):
    actions_template = "admin/blanket/tf10/link.html"
    extend_template = "admin/admin_layout.html"

    def get_context_data(self, **kwargs):
        context = super(TF10ListView, self).get_context_data(**kwargs)
        context["title"] = "Afgiftsanmeldelser"
        context["can_create"] = False
        return context


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


class AfgiftstabelDetailView(LoginRequiredMixin, HasRestClientMixin, FormView):
    template_name = "admin/afgiftstabel/view.html"
    form_class = forms.AfgiftstabelUpdateForm

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **{
                **kwargs,
                "object": self.item,
                "can_edit": self.item.kladde or self.item.gyldig_fra > date.today(),
            }
        )

    def get_initial(self):
        return {
            "gyldig_fra": self.item.gyldig_fra,
            "kladde": self.item.kladde,
        }

    def form_valid(self, form):
        tabel_id = self.item.id
        if form.cleaned_data["delete"]:
            if self.item.kladde:
                self.rest_client.afgiftstabel.delete(tabel_id)
            return redirect(reverse("afgiftstabel_list"))
        try:
            if self.item.kladde or self.item.gyldig_fra > date.today():
                self.rest_client.afgiftstabel.update(tabel_id, form.cleaned_data)
            return redirect(reverse("afgiftstabel_list"))
        except HTTPError as e:
            if e.response.status_code == 404:
                raise Http404("Afgiftstabel findes ikke")
            raise

    @cached_property
    def item(self) -> Afgiftstabel:
        try:
            afgiftstabel = Afgiftstabel.from_dict(
                self.rest_client.get(f"afgiftstabel/{self.kwargs['id']}")
            )
            afgiftstabel.vareafgiftssatser = self.get_satser()
        except HTTPError as e:
            if e.response.status_code == 404:
                raise Http404("Afgiftstabel findes ikke")
            raise
        return afgiftstabel

    def get_satser(self):
        satser = [
            Vareafgiftssats.from_dict(result)
            for result in self.rest_client.get(
                "vareafgiftssats", {"afgiftstabel": self.kwargs["id"]}
            )["items"]
        ]
        by_overordnet = defaultdict(list)
        for sats in satser:
            if sats.overordnet:
                by_overordnet[sats.overordnet].append(sats)
        for sats in satser:
            sats.populate_subs(lambda id: by_overordnet.get(id))
        return satser


class AfgiftstabelDownloadView(HasRestClientMixin, View):
    valid_formats = ("xlsx", "csv")
    headers = (
        "afgiftsgruppenummer",
        "overordnet",
        "vareart",
        "enhed",
        "afgiftssats",
        "kræver_indførselstilladelse",
        "minimumsbeløb",
        "segment_nedre",
        "segment_øvre",
    )

    def get(self, request, *args, **kwargs):
        format = kwargs["format"]
        if format not in self.valid_formats:
            return HttpResponseBadRequest(
                f"Ugyldigt format {format}. Gyldige formater: {', '.join(self.valid_formats)}"
            )

        afgiftstabel = self.rest_client.get(f"afgiftstabel/{kwargs['id']}")
        items = [
            Vareafgiftssats.from_dict(item)
            for item in self.rest_client.get(
                f"vareafgiftssats", {"afgiftstabel": kwargs["id"]}
            )["items"]
        ]

        items_by_id = {item.id: item for item in items}
        rows = [
            list(item.spreadsheet_row(self.headers, lambda id: items_by_id[id]))
            for item in items
        ]

        if afgiftstabel["kladde"]:
            filename = f"Afgiftstabel_kladde.{format}"
        else:
            filename = (
                f"Afgiftstabel_"
                f"{afgiftstabel['gyldig_fra']}_"
                f"{afgiftstabel['gyldig_til'] if afgiftstabel['gyldig_til'] else 'altid'}."
                f"{format}"
            )

        if format == "xlsx":
            return self.render_xlsx(self.headers_pretty, rows, filename)
        if format == "csv":
            return self.render_csv(self.headers_pretty, rows, filename)

    @cached_property
    def headers_pretty(self):
        return [header.replace("_", " ").capitalize() for header in self.headers]

    def render_xlsx(
        self,
        headers: Iterable[str],
        items: Iterable[Iterable[Union[str, int, bool]]],
        filename: str,
    ) -> HttpResponse:
        wb = Workbook(write_only=True)
        ws = wb.create_sheet()
        ws.append(headers)
        for item in items:
            ws.append(item)
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename={}".format(filename)},
        )
        wb.save(response)
        return response

    def render_csv(
        self,
        headers: Iterable[str],
        items: Iterable[Iterable[Union[str, int, bool]]],
        filename: str,
    ) -> HttpResponse:
        response = HttpResponse(
            content_type="text/csv",
            headers={"Content-Disposition": "attachment; filename={}".format(filename)},
        )
        writer = csv.writer(response)
        writer.writerow(headers)
        for item in items:
            writer.writerow(item)
        return response
