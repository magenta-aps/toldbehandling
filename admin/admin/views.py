# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import csv
from datetime import date, datetime
from functools import cached_property
from typing import Any, Dict, Iterable, List, Optional, Set, Union

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.template import loader
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import FormView, TemplateView
from openpyxl import Workbook
from requests import HTTPError
from told_common import views as common_views
from told_common.util import filter_dict_values, join_words, render_pdf

from admin import forms
from admin.clients.prisme import PrismeException, send_afgiftsanmeldelse
from admin.spreadsheet import VareafgiftssatsSpreadsheetUtil

from django.http import (  # isort: skip
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
)
from told_common.data import (  # isort: skip
    Afgiftstabel,
    Forsendelsestype,
    Vareafgiftssats,
    PrismeResponse,
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
    def get_subsatser(self, parent_id: int) -> List[Vareafgiftssats]:
        return self.rest_client.vareafgiftssats.list(overordnet=parent_id)


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
    form_class = forms.TF10ViewForm

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **{
                **kwargs,
                "object": self.object,
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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["initial"] = {}
        # indberetter = self.object.oprettet_på_vegne_af or self.object.oprettet_af
        indberetter = self.object.oprettet_af
        if indberetter and "indberetter_data" in indberetter:
            cvr = indberetter["indberetter_data"]["cvr"]
            kategorier = [
                item["kategori"]
                for item in settings.CVR_TOLDKATEGORI_MAP
                if cvr in item["cvr"]
            ]
            if kategorier:
                kwargs["initial"]["toldkategori"] = kategorier[0]
        return kwargs

    def form_valid(self, form):
        anmeldelse_id = self.kwargs["id"]
        send_til_prisme = form.cleaned_data["send_til_prisme"]
        godkendt = form.cleaned_data["godkendt"]
        notat = (
            form.cleaned_data["notat1"]
            or form.cleaned_data["notat2"]
            or form.cleaned_data["notat3"]
        )
        toldkategori = form.cleaned_data["toldkategori"]
        if toldkategori and toldkategori != self.object.toldkategori:
            self.rest_client.afgiftanmeldelse.set_toldkategori(
                anmeldelse_id, toldkategori
            )

        try:
            if send_til_prisme:
                # Yderligere tjek for om brugeren må ændre noget.
                # Vi kan have en situation hvor brugeren må se siden men ikke submitte formularen
                response = self.check_permissions(self.prisme_permissions)
                if response:
                    return response
                anmeldelse = self.rest_client.afgiftanmeldelse.get(
                    anmeldelse_id, full=True, include_varelinjer=True
                )
                try:
                    responses = send_afgiftsanmeldelse(anmeldelse)
                    # Gem data
                    for response in responses:
                        self.rest_client.prismeresponse.create(
                            PrismeResponse(
                                id=None,
                                afgiftsanmeldelse=anmeldelse,
                                rec_id=response.record_id,
                                tax_notification_number=response.tax_notification_number,
                                delivery_date=datetime.fromisoformat(
                                    response.delivery_date
                                ),
                            )
                        )
                except PrismeException as e:
                    messages.add_message(
                        self.request,
                        messages.ERROR,
                        f"Besked ikke sendt til Prisme; {e.message}",
                    )

            elif godkendt is not None:
                # Yderligere tjek for om brugeren må ændre noget.
                # Vi kan have en situation hvor brugeren må se siden men ikke submitte formularen
                response = self.check_permissions(self.edit_permissions)
                if response:
                    return response
                self.rest_client.afgiftanmeldelse.set_godkendt(anmeldelse_id, godkendt)

                if godkendt == False:
                    anmeldelse = self.rest_client.afgiftanmeldelse.get(
                        anmeldelse_id, full=True, include_varelinjer=True
                    )
                    indberetter_data = anmeldelse.oprettet_af["indberetter_data"]
                    domain = settings.HOST_DOMAIN or "http://localhost"
                    pdf = render_pdf(
                        "admin/blanket/tf10/afvist.html",
                        {
                            "link": f"{domain}/blanket/tf10/{anmeldelse_id}",
                            "notat": notat,
                        },
                    )
                    self.rest_client.eboks.create(
                        {
                            "cpr": indberetter_data.get("cpr"),
                            "cvr": indberetter_data.get("cvr"),
                            "titel": "Din afgiftsanmeldelse (TF10) er afvist",
                            "pdf": pdf,
                        }
                    )
                    # For at inspicere pdf'en
                    # return HttpResponse(content=pdf, content_type="application/pdf")

            # Opret notat _efter_ den nye version af anmeldelsen, så vores historik-filtrering fungerer
            if notat:
                self.rest_client.notat.create({"tekst": notat}, self.kwargs["id"])

        except HTTPError as e:
            if e.response.status_code == 404:
                raise Http404("Afgiftsanmeldelse findes ikke")
            raise
        return redirect(reverse("tf10_view", kwargs={"id": anmeldelse_id}))

    @cached_property
    def object(self):
        id = self.kwargs["id"]
        try:
            anmeldelse = self.rest_client.afgiftanmeldelse.get(
                id,
                full=True,
                include_notater=True,
                include_varelinjer=True,
                include_prismeresponses=True,
            )
        except HTTPError as e:
            if e.response.status_code == 404:
                raise Http404("Afgiftsanmeldelse findes ikke")
            raise
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
        context["can_create"] = True
        context["can_view"] = TF10View.has_permissions(request=self.request)
        context["can_edit_multiple"] = True
        context["multiedit_url"] = reverse("tf10_edit_multiple")
        return context


class TF10FormCreateView(common_views.TF10FormCreateView):
    extend_template = "admin/admin_layout.html"
    required_permissions = (
        "auth.admin",
        *common_views.TF10FormCreateView.required_permissions,
    )
    form_class = forms.TF10CreateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        count, users = self.rest_client.user.list(group="Indberettere", limit=100000)
        kwargs["oprettet_på_vegne_af_choices"] = tuple(
            (
                user.id,
                join_words(
                    [
                        user.first_name,
                        user.last_name,
                        f"(CVR: {user.cvr})" if user.cvr else None,
                    ]
                ),
            )
            for user in users
        )
        return kwargs

    def get_context_data(self, **context):
        return super().get_context_data(
            **{**context, "vis_notater": False, "admin": True, "gem_top": False}
        )


class TF10FormUpdateView(common_views.TF10FormUpdateView):
    extend_template = "admin/admin_layout.html"
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
            **{
                **context,
                "vis_notater": True,
                "admin": True,
                "gem_top": True,
                "notater": self.rest_client.notat.list(self.kwargs["id"]),
            }
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
        id = self.kwargs["id"]
        self.notater = {item.index: item for item in self.rest_client.notat.list(id)}
        count, items = self.rest_client.afgiftanmeldelse.list_history(id)
        return {"count": count, "items": items}

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
        value = getattr(item, key)
        if key == "history_date":
            if type(value) is str:
                value = datetime.fromisoformat(value)
            return value.astimezone().strftime("%Y-%m-%d %H:%M:%S")

        if value is None:
            value = ""
        return value


class TF10HistoryDetailView(PermissionsRequiredMixin, TF10BaseView, TemplateView):
    template_name = "admin/blanket/tf10/history/view.html"

    def get_object(self):
        return self.rest_client.afgiftanmeldelse.get_history_item(
            self.kwargs["id"], self.kwargs["index"]
        )

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
            count, items = self.rest_client.afgiftanmeldelse.list(
                id=self.ids, full=True
            )
            return items
        return []

    @cached_property
    def fragttyper(self) -> Set[str]:
        fragttyper = set()
        for item in self.items:
            if item.fragtforsendelse:
                fragttyper.add(
                    "skibsfragt"
                    if item.fragtforsendelse.forsendelsestype == Forsendelsestype.SKIB
                    else "luftfragt"
                )
            if item.postforsendelse:
                fragttyper.add(
                    "skibspost"
                    if item.postforsendelse.forsendelsestype == Forsendelsestype.SKIB
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
                {
                    field: form.cleaned_data.get(field)
                    for field in (
                        "forbindelsesnr",
                        "afgangsdato",
                    )
                },
                (None, ""),
            )
            if self.fælles_fragttype in ("skibsfragt", "luftfragt"):
                fragt_update_data["fragttype"] = self.fælles_fragttype
                for item in self.items:
                    self.rest_client.fragtforsendelse.update(
                        item.fragtforsendelse.id, fragt_update_data
                    )
            if self.fælles_fragttype in ("skibspost", "luftpost"):
                fragt_update_data["fragttype"] = self.fælles_fragttype
                for item in self.items:
                    self.rest_client.postforsendelse.update(
                        item.postforsendelse.id, fragt_update_data
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
                and item["gyldig_fra"] <= today
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
        return self.rest_client.vareafgiftssats.list(afgiftstabel=self.kwargs["id"])


class AfgiftstabelDownloadView(PermissionsRequiredMixin, HasRestClientMixin, View):
    required_permissions = (
        "auth.admin",
        "sats.view_afgiftstabel",
        "sats.view_vareafgiftssats",
    )
    valid_formats = ("xlsx", "csv")
    headers = (
        ("afgiftsgruppenummer", "Afgiftsgruppenummer"),
        ("overordnet", "Overordnet"),
        ("vareart_da", "Vareart (da)"),
        ("vareart_kl", "Vareart (kl)"),
        ("enhed", "Enhed"),
        ("afgiftssats", "Afgiftssats"),
        ("kræver_indførselstilladelse", "Kræver indførselstilladelse"),
        ("har_privat_tillægsafgift_alkohol", "Har privat tillægsafgift alkohol"),
        ("minimumsbeløb", "Minimumsbeløb"),
        ("segment_nedre", "Segment nedre"),
        ("segment_øvre", "Segment øvre"),
    )

    def get(self, request, *args, **kwargs):
        format = kwargs["format"]
        if format not in self.valid_formats:
            return HttpResponseBadRequest(
                f"Ugyldigt format {format}. Gyldige formater: {', '.join(self.valid_formats)}"
            )

        id = kwargs["id"]
        afgiftstabel = self.rest_client.afgiftstabel.get(id)
        items = self.rest_client.vareafgiftssats.list(afgiftstabel=id)

        items_by_id = {item.id: item for item in items}
        rows = [
            list(
                VareafgiftssatsSpreadsheetUtil.spreadsheet_row(
                    item,
                    [header[0] for header in self.headers],
                    lambda id: items_by_id[id],
                )
            )
            for item in items
        ]

        if afgiftstabel.kladde:
            filename = f"Afgiftstabel_kladde.{format}"
        else:
            filename = (
                f"Afgiftstabel_"
                f"{afgiftstabel.gyldig_fra}_"
                f"{afgiftstabel.gyldig_til if afgiftstabel.gyldig_til else 'altid'}."
                f"{format}"
            )
        headers_pretty = [header[1] for header in self.headers]
        if format == "xlsx":
            return self.render_xlsx(headers_pretty, rows, filename)
        if format == "csv":
            return self.render_csv(headers_pretty, rows, filename)

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
