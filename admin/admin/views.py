# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import csv
from datetime import date, datetime
from functools import cached_property
from typing import Any, Dict, Iterable, List, Optional, Set, Union
from urllib.parse import unquote

from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.template import loader
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import FormView, TemplateView
from openpyxl import Workbook
from requests import HTTPError
from told_common import views as common_views
from told_common.data import Afgiftstabel, Vareafgiftssats
from told_common.util import filter_dict_values

from admin import forms
from admin.spreadsheet import VareafgiftssatsSpreadsheetUtil

from django.http import (  # isort: skip
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
)
from told_common.view_mixins import (  # isort: skip
    GetFormView,
    HasRestClientMixin,
    PermissionsRequiredMixin,
)


class IndexView(PermissionsRequiredMixin, HasRestClientMixin, TemplateView):
    template_name = "admin/index.html"
    required_permissions = ("auth.admin",)

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


class TF10BaseView(HasRestClientMixin):
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


class TF10View(PermissionsRequiredMixin, TF10BaseView, FormView):
    required_permissions = (
        "auth.admin",
        "aktør.view_afsender",
        "aktør.view_modtager",
        "forsendelse.view_postforsendelse",
        "forsendelse.view_fragtforsendelse",
        "anmeldelse.view_afgiftsanmeldelse",
        "anmeldelse.view_varelinje",
        "sats.view_vareafgiftssats",
    )
    edit_permissions = ("anmeldelse.change_afgiftsanmeldelse",)
    prisme_permissions = ("anmeldelse.prisme_afgiftsanmeldelse",)

    template_name = "admin/blanket/tf10/view.html"
    form_class = forms.TF10GodkendForm

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **{
                **kwargs,
                "object": self.get_object(),
                "can_edit": self.has_permissions(
                    request=self.request, required_permissions=self.edit_permissions
                ),
                "can_send_prisme": self.has_permissions(
                    request=self.request, required_permissions=self.prisme_permissions
                ),
                "can_view_history": TF10HistoryListView.has_permissions(
                    request=self.request
                ),
            }
        )

    def form_valid(self, form):
        # Yderligere tjek for om brugeren må ændre noget.
        # Vi kan have en situation hvor brugeren må se siden men ikke submitte formularen
        response = self.check_permissions(self.edit_permissions)
        if response:
            return response
        godkendt = form.cleaned_data["godkendt"]
        anmeldelse_id = self.kwargs["id"]
        try:
            self.rest_client.afgiftanmeldelse.set_godkendt(anmeldelse_id, godkendt)
            # Opret notat _efter_ den nye version af anmeldelsen, så vores historik-filtrering fungerer
            notat = form.cleaned_data["notat"]
            if notat:
                self.rest_client.notat.create({"tekst": notat}, self.kwargs["id"])
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
        anmeldelse["varelinjer"] = self.rest_client.varelinje.list(anmeldelse["id"])
        for varelinje in anmeldelse["varelinjer"]:
            sats_id = varelinje["vareafgiftssats"]
            varelinje["vareafgiftssats"] = self.get_sats(sats_id)
        anmeldelse["notater"] = self.rest_client.notat.list(anmeldelse["id"])
        return anmeldelse


class TF10ListView(common_views.TF10ListView):
    actions_template = "admin/blanket/tf10/link.html"
    extend_template = "admin/admin_layout.html"
    required_permissions = (
        "auth.admin",
        *common_views.TF10ListView.required_permissions,
    )

    def get_context_data(self, **kwargs):
        context = super(TF10ListView, self).get_context_data(**kwargs)
        context["title"] = "Afgiftsanmeldelser"
        context["can_create"] = False
        context["can_view"] = TF10View.has_permissions(request=self.request)
        context["can_edit_multiple"] = True
        context["multiedit_url"] = reverse("tf10_edit_multiple")
        return context


class TF10FormUpdateView(common_views.TF10FormUpdateView):
    extend_template = "admin/admin_layout.html"
    template_name = "admin/blanket/tf10/form.html"
    form_class = forms.TF10UpdateForm
    required_permissions = (
        "auth.admin",
        *common_views.TF10FormUpdateView.required_permissions,
    )

    def form_valid(self, form, formset):
        response = super().form_valid(form, formset)
        # Opret notat _efter_ den nye version af anmeldelsen, så vores historik-filtrering fungerer
        notat = form.cleaned_data["notat"]
        if notat:
            self.rest_client.notat.create({"tekst": notat}, self.kwargs["id"])
        return response

    def get_context_data(self, **context):
        return super().get_context_data(
            **{**context, "notater": self.rest_client.notat.list(self.kwargs["id"])}
        )


class TF10HistoryListView(
    PermissionsRequiredMixin, HasRestClientMixin, common_views.ListView
):
    required_permissions = (
        "aktør.view_afsender",
        "aktør.view_modtager",
        "forsendelse.view_postforsendelse",
        "forsendelse.view_fragtforsendelse",
        "anmeldelse.view_afgiftsanmeldelse",
        "anmeldelse.view_varelinje",
    )
    template_name = "admin/blanket/tf10/history/list.html"
    actions_template = "admin/blanket/tf10/history/actions.html"

    def __init__(self, *args, **kwargs):
        self.notater = {}
        super().__init__(*args, **kwargs)

    def get_context_data(self, **context):
        return super().get_context_data(
            **{
                **context,
                "id": self.kwargs["id"],
                "actions_template": self.actions_template,
                "can_view": TF10HistoryDetailView.has_permissions(request=self.request),
            }
        )

    def get_items(self, search_data: Dict[str, Any]):
        self.notater = {
            item.index: item for item in self.rest_client.notat.list(self.kwargs["id"])
        }
        return self.rest_client.get(f"afgiftsanmeldelse/{self.kwargs['id']}/history")

    def item_to_json_dict(
        self, item: Dict[str, Any], context: Dict[str, Any], index: int
    ) -> Dict[str, Any]:
        return {
            key: self.map_value(item, key, context, index)
            for key in ("history_username", "history_date", "notat", "actions")
        }

    def map_value(self, item, key, context, index):
        if key == "actions":
            return loader.render_to_string(
                self.actions_template,
                {"item": item, "index": index, **context},
                self.request,
            )
        if key == "notat":
            if index in self.notater:
                return self.notater[index].tekst
            return ""
        value = item[key]
        if key == "history_date":
            return (
                datetime.fromisoformat(value).astimezone().strftime("%Y-%m-%d %H:%M:%S")
            )
        if value is None:
            value = ""
        return value


class TF10HistoryDetailView(PermissionsRequiredMixin, TF10BaseView, TemplateView):
    template_name = "admin/blanket/tf10/history/view.html"

    def get_object(self):
        anmeldelse = self.rest_client.get(
            f"afgiftsanmeldelse/{self.kwargs['id']}/history/{self.kwargs['index']}"
        )
        anmeldelse["varelinjer"] = self.rest_client.get(
            "varelinje",
            {
                "afgiftsanmeldelse": anmeldelse["id"],
                "afgiftsanmeldelse_history_index": self.kwargs["index"],
            },
        )["items"]
        for varelinje in anmeldelse["varelinjer"]:
            sats_id = varelinje["vareafgiftssats"]
            varelinje["vareafgiftssats"] = self.get_sats(sats_id)

        anmeldelse["notater"] = self.rest_client.notat.list(
            anmeldelse["id"], self.kwargs["index"]
        )
        return anmeldelse

    def get_context_data(self, **context):
        return super().get_context_data(
            **{
                **context,
                "object": self.get_object(),
                "index": self.kwargs["index"],
            }
        )


class TF10EditMultipleView(PermissionsRequiredMixin, HasRestClientMixin, FormView):
    template_name = "admin/blanket/tf10/multi.html"
    form_class = forms.TF10UpdateMultipleForm
    success_url = reverse_lazy("tf10_list")
    required_permissions = (
        "auth.admin",
        "forsendelse.change_postforsendelse",
        "forsendelse.change_fragtforsendelse",
        "anmeldelse.change_afgiftsanmeldelse",
    )

    def dispatch(self, request, *args, **kwargs):
        try:
            self.ids = [int(id) for id in self.request.GET.getlist("id")]
        except ValueError as e:
            return HttpResponseBadRequest("Invalid id value")
        if not self.ids:
            return HttpResponseBadRequest("Missing id value")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if len(self.ids) == 1:
            return redirect("tf10_edit", id=self.ids[0])
        return super().get(request, *args, **kwargs)

    @cached_property
    def items(self) -> List[Dict]:
        if self.ids:
            return self.rest_client.afgiftanmeldelse.get({"id": self.ids})
        return []

    @cached_property
    def fragttyper(self) -> Set[str]:
        fragttyper = set()
        for item in self.items:
            if item["fragtforsendelse"]:
                fragtforsendelse = self.rest_client.fragtforsendelse.get(
                    item["fragtforsendelse"]
                )
                fragttyper.add(
                    "skibsfragt"
                    if fragtforsendelse["forsendelsestype"] == "S"
                    else "luftfragt"
                )
            if item["postforsendelse"]:
                fragtforsendelse = self.rest_client.postforsendelse.get(
                    item["postforsendelse"]
                )
                fragttyper.add(
                    "skibspost"
                    if fragtforsendelse["forsendelsestype"] == "S"
                    else "luftpost"
                )
        return fragttyper

    @cached_property
    def fælles_fragttype(self) -> Optional[str]:
        if len(self.fragttyper) == 1:
            return list(self.fragttyper)[0]
        return None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["fragttype"] = self.fælles_fragttype
        return kwargs

    def get_context_data(self, **context: Dict[str, Any]) -> Dict[str, Any]:
        return super().get_context_data(
            **{
                **context,
                "items": self.items,
                "fælles_fragttype": self.fælles_fragttype,
            }
        )

    def form_valid(self, form):
        if self.fælles_fragttype:
            fragt_update_data = filter_dict_values(
                {field: form.cleaned_data.get(field) for field in ("forbindelsesnr")},
                (None, ""),
            )
            if self.fælles_fragttype in ("skibsfragt", "luftfragt"):
                fragt_update_data["fragttype"] = self.fælles_fragttype
                for item in self.items:
                    self.rest_client.fragtforsendelse.update(
                        item["fragtforsendelse"], fragt_update_data
                    )
            if self.fælles_fragttype in ("skibspost", "luftpost"):
                fragt_update_data["fragttype"] = self.fælles_fragttype
                for item in self.items:
                    self.rest_client.postforsendelse.update(
                        item["postforsendelse"], fragt_update_data
                    )

        notat = form.cleaned_data["notat"]
        for id in self.ids:
            # Dummy-opdatering indtil vi har noget rigtig data at opdatere med.
            # Skal dog gøres for at vi har en ny version at putte et notat på
            self.rest_client.afgiftanmeldelse.update(id, {}, None, force_write=True)
            # Opret notat _efter_ den nye version af anmeldelsen, så vores historik-filtrering fungerer
            if notat:
                self.rest_client.notat.create({"tekst": notat}, id)
        return super().form_valid(form)


class AfgiftstabelListView(PermissionsRequiredMixin, HasRestClientMixin, GetFormView):
    required_permissions = (
        "auth.admin",
        "sats.view_afgiftstabel",
        "common.admin_site_access",
    )
    template_name = "admin/afgiftstabel/list.html"
    form_class = forms.AfgiftstabelSearchForm
    actions_template = "admin/afgiftstabel/handlinger.html"
    list_size = 20

    def get_context_data(self, **context):
        return super().get_context_data(
            **{
                **context,
                "actions_template": self.actions_template,
                "can_upload": self.can_upload,
                "can_download": self.can_download,
            }
        )

    @cached_property
    def can_upload(self):
        return AfgiftstabelCreateView.has_permissions(request=self.request)

    @cached_property
    def can_download(self):
        return AfgiftstabelDownloadView.has_permissions(request=self.request)

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
        # // = Python floor division
        search_data["page_number"] = (search_data["offset"] // search_data["limit"]) + 1
        response = self.rest_client.get("afgiftstabel", search_data)
        total = response["count"]
        items = response["items"]
        context = self.get_context_data(
            items=items, total=total, search_data=search_data
        )
        items = [
            {
                key: self.map_value(item, key)
                for key in (
                    "id",
                    "gyldig_fra",
                    "gyldig_til",
                    "kladde",
                    "actions",
                    "gældende",
                )
            }
            for item in items
        ]
        context["items"] = items
        if form.cleaned_data["json"]:
            return JsonResponse(
                {
                    "total": total,
                    "items": items,
                }
            )
        return self.render_to_response(context)

    def map_value(self, item, key):
        value = item.get(key, None)
        if key == "actions":
            return loader.render_to_string(
                self.actions_template,
                {"item": item, "can_download": self.can_download},
                self.request,
            )
        if key == "gældende":
            today = date.today().isoformat()
            value = (
                not item["kladde"]
                and item["gyldig_fra"] < today
                and (item["gyldig_til"] is None or today < item["gyldig_til"])
            )
        return value


class AfgiftstabelDetailView(PermissionsRequiredMixin, HasRestClientMixin, FormView):
    required_permissions = (
        "auth.admin",
        "sats.view_afgiftstabel",
        "sats.view_vareafgiftssats",
    )
    edit_permissions = ("sats.change_afgiftstabel",)
    delete_permissions = ("sats.delete_afgiftstabel",)
    template_name = "admin/afgiftstabel/view.html"
    form_class = forms.AfgiftstabelUpdateForm

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **{
                **kwargs,
                "object": self.item,
                "can_edit": (self.item.kladde or self.item.gyldig_fra > date.today())
                and self.has_permissions(
                    request=self.request, required_permissions=self.edit_permissions
                ),
                "can_delete": self.item.kladde
                and self.has_permissions(
                    request=self.request, required_permissions=self.delete_permissions
                ),
                "can_download": AfgiftstabelDownloadView.has_permissions(
                    request=self.request
                ),
            }
        )

    def get_initial(self):
        return {
            "gyldig_fra": self.item.gyldig_fra,
            "kladde": self.item.kladde,
        }

    def form_valid(self, form):
        response = self.check_permissions(
            self.edit_permissions
        )  # Access denied view hvis permissions fejler
        if response:
            return response
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
            afgiftstabel = self.rest_client.afgiftstabel.get(self.kwargs["id"])
            afgiftstabel.vareafgiftssatser = self.get_satser()
        except HTTPError as e:
            if e.response.status_code == 404:
                raise Http404("Afgiftstabel findes ikke")
            raise
        return afgiftstabel

    def get_satser(self):
        return self.rest_client.vareafgiftssats.list(self.kwargs["id"])


class AfgiftstabelDownloadView(PermissionsRequiredMixin, HasRestClientMixin, View):
    required_permissions = (
        "auth.admin",
        "sats.view_afgiftstabel",
        "sats.view_vareafgiftssats",
    )
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
                "vareafgiftssats", {"afgiftstabel": kwargs["id"]}
            )["items"]
        ]

        items_by_id = {item.id: item for item in items}
        rows = [
            list(
                VareafgiftssatsSpreadsheetUtil.spreadsheet_row(
                    item, self.headers, lambda id: items_by_id[id]
                )
            )
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


class AfgiftstabelCreateView(PermissionsRequiredMixin, HasRestClientMixin, FormView):
    template_name = "admin/afgiftstabel/form.html"
    form_class = forms.AfgiftstabelCreateForm
    required_permissions = (
        "auth.admin",
        "sats.add_afgiftstabel",
        "sats.add_vareafgiftssats",
    )

    def get_success_url(self):
        return reverse("afgiftstabel_list")

    def form_valid(self, form):
        satser = form.parsed_satser
        self.save(satser)
        return super().form_valid(form)

    def save(self, satser: List[Dict[str, Union[str, int, bool]]]) -> int:
        tabel_id = self.rest_client.afgiftstabel.create({})
        afgiftsgruppenummer_to_id = {}
        by_afgiftsgruppenummer = {x["afgiftsgruppenummer"]: x for x in satser}

        # Sørg for at vi opretter alle overordnede før deres underordnede
        def save_one(vareafgiftssats: Dict[str, Union[str, int, bool]]):
            afgiftsgruppenummer = vareafgiftssats["afgiftsgruppenummer"]
            if afgiftsgruppenummer not in afgiftsgruppenummer_to_id:
                overordnet = vareafgiftssats["overordnet"]
                if overordnet is not None:
                    if overordnet not in afgiftsgruppenummer_to_id:
                        save_one(by_afgiftsgruppenummer[overordnet])
                    vareafgiftssats["overordnet_id"] = afgiftsgruppenummer_to_id[
                        overordnet
                    ]
                vareafgiftssats["afgiftstabel_id"] = tabel_id
                sats_id = self.rest_client.vareafgiftssats.create(vareafgiftssats)
                afgiftsgruppenummer_to_id[afgiftsgruppenummer] = sats_id

        for vareafgiftssats in satser:
            save_one(vareafgiftssats)
        return tabel_id
