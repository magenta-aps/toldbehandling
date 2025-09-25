# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
import logging
from datetime import datetime, timezone
from decimal import Context, Decimal
from functools import cached_property
from typing import Any, Dict, List, Optional, Set, Union
from urllib.parse import quote_plus

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponseBadRequest, JsonResponse, QueryDict
from django.shortcuts import redirect
from django.template import loader
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import FormView, TemplateView
from requests import HTTPError
from told_common import views as common_views
from told_common.data import (
    Afgiftsanmeldelse,
    Afgiftstabel,
    Forsendelsestype,
    PrismeResponse,
    Vareafgiftssats,
)
from told_common.util import filter_dict_values, format_daterange, join, join_words
from told_common.view_mixins import (
    CatchErrorsMixin,
    FormWithFormsetView,
    GetFormView,
    HasRestClientMixin,
    LoginRequiredMixin,
    PermissionsRequiredMixin,
    PreventDoubleSubmitMixin,
)

from admin import forms
from admin.clients.prisme import (
    PrismeConnectionException,
    PrismeException,
    PrismeHttpException,
    send_afgiftsanmeldelse,
)
from admin.spreadsheet import SpreadsheetExport, VareafgiftssatsSpreadsheetUtil
from admin.utils import send_email

log = logging.getLogger(__name__)


class TwofactorAuthRequiredMixin(LoginRequiredMixin):
    def login_check(self):
        redir = super().login_check()
        if redir:
            return redir
        # settings.REQUIRE_2FA can be removed after September 1.
        user = self.request.user
        if settings.REQUIRE_2FA and not user.twofactor_enabled:
            return redirect(reverse("twofactor:setup"))
        elif user.twofactor_enabled and not self.request.session.get(
            "twofactor_authenticated"
        ):
            return redirect(
                reverse("twofactor:login") + "?back=" + quote_plus(self.request.path)
            )

        return None


class AdminLayoutBaseView(
    CatchErrorsMixin,
    TwofactorAuthRequiredMixin,
    PermissionsRequiredMixin,
    HasRestClientMixin,
):
    """Base view for admin pages, using a common layout with navigation.

    NOTE: We do not set default required-permissions in this view, yet, since they
    will currently be overridden by the child-views equivalent.. we need a way to
    combine them for if we want default permissions for this view.
    """

    extend_template = "admin/admin_layout.html"

    # NOTE: We add 'auth.admin' since its for navigation on the admin-page
    permissions_view_afgiftstabeller = (
        "auth.admin",
        "sats.view_afgiftstabel",
    )
    permissions_view_afgiftsanmeldelser = (
        "auth.admin",
        *common_views.TF10ListView.required_permissions,
    )
    permissions_view_privatafgiftsanmeldelser = (
        "auth.admin",
        *common_views.TF5ListView.required_permissions,
    )

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **{
                **kwargs,
                "nav_afgiftstabeller": self.has_permissions(
                    request=self.request,
                    required_permissions=self.permissions_view_afgiftstabeller,
                ),
                "nav_afgiftsanmeldelser": self.has_permissions(
                    request=self.request,
                    required_permissions=self.permissions_view_afgiftsanmeldelser,
                ),
                "nav_privatafgiftsanmeldelser": self.has_permissions(
                    request=self.request,
                    required_permissions=self.permissions_view_privatafgiftsanmeldelser,
                ),
                "environment": settings.ENVIRONMENT,
                "version": settings.VERSION,
            }
        )


class TF10View(
    AdminLayoutBaseView, PreventDoubleSubmitMixin, common_views.TF10View, FormView
):
    required_permissions = ("auth.admin", *common_views.TF10View.required_permissions)
    prisme_permissions = (
        "anmeldelse.prisme_afgiftsanmeldelse",
        "aktør.change_modtager",
        "aktør.view_afsender",
        "aktør.view_modtager",
        "forsendelse.view_postforsendelse",
        "forsendelse.view_fragtforsendelse",
        "anmeldelse.view_afgiftsanmeldelse",
        "anmeldelse.view_varelinje",
    )
    form_class = forms.TF10ViewForm
    extend_template = "admin/admin_layout.html"

    @cached_property
    def toldkategorier(self):
        return self.rest_client.toldkategori.list()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_approve = self.has_permissions(
            request=self.request, required_permissions=self.edit_permissions
        )

        context.update(
            {
                "admin_ui": True,
                "can_godkend": can_approve,
                "can_afvis": can_approve,
                "can_edit": TF10FormUpdateView.has_permissions(request=self.request),
                "can_send_prisme": self.has_permissions(
                    request=self.request, required_permissions=self.prisme_permissions
                ),
                "can_view_history": TF10HistoryListView.has_permissions(
                    request=self.request
                ),
                "show_stedkode": True,
            }
        )
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["toldkategorier"] = self.toldkategorier
        return kwargs

    def form_valid(self, form):
        anmeldelse_id = self.kwargs["id"]
        send_til_prisme = form.cleaned_data["send_til_prisme"]
        status = form.cleaned_data["status"]
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
        stedkode = form.cleaned_data["modtager_stedkode"]
        if stedkode and stedkode != self.object.modtager.stedkode:
            self.rest_client.modtager.update(
                self.object.modtager.id, {"stedkode": stedkode}
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
                    kræver_cvr = {
                        item.kategori for item in self.toldkategorier if item.kræver_cvr
                    }
                    if anmeldelse.toldkategori in kræver_cvr:
                        cvr = None
                        if anmeldelse.betales_af == "afsender":
                            cvr = anmeldelse.afsender.cvr
                        elif anmeldelse.betales_af == "modtager":
                            cvr = anmeldelse.modtager.cvr
                        # elif anmeldelse.betales_af == "indberetter":
                        #     cvr = anmeldelse.indberetter["indberetter_data"]["cvr"]
                        if not cvr:
                            raise ValidationError(
                                f"For toldkategori {anmeldelse.toldkategori} skal der angives et "
                                f"CVR-nummer på betaleren, som er enten afsender eller modtager",
                            )

                    responses = send_afgiftsanmeldelse(anmeldelse)
                    # Gem data
                    for response in responses:
                        try:
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
                        except:
                            log.error(
                                f"Anmeldelse {anmeldelse.id} sendt til prisme, "
                                f"men fejlede under oprettelse af PrismeResponse"
                            )
                            raise
                    if len(responses) == 0:
                        log.error(
                            f"Anmeldelse {anmeldelse.id} sendt til prisme, men fik ikke noget svar"
                        )
                except (
                    PrismeException,
                    PrismeHttpException,
                    ValidationError,
                    PrismeConnectionException,
                ) as e:
                    messages.add_message(
                        self.request,
                        messages.ERROR,
                        f"Anmeldelse ikke sendt til Prisme. Fejlbesked:\n{e.message}",
                    )
                    log.error(
                        f"Anmeldelse {anmeldelse.id} ikke sendt til Prisme", exc_info=e
                    )
            elif status:
                # Yderligere tjek for om brugeren må ændre noget.
                # Vi kan have en situation hvor brugeren må se siden men ikke submitte formularen
                response = self.check_permissions(self.edit_permissions)
                if response:
                    return response

                if status == "afvist":
                    if not notat:
                        raise Exception(
                            "Afgiftsanmeldelser kan ikke afvises uden et notat"
                        )

                    # Get current anmeldelse
                    anmeldelse = self.rest_client.afgiftanmeldelse.get(
                        anmeldelse_id, full=True, include_varelinjer=True
                    )

                    # UPDATE
                    self.rest_client.afgiftanmeldelse.set_status(anmeldelse_id, status)
                    self.rest_client.notat.create({"tekst": notat}, self.kwargs["id"])

                    if (
                        settings.EMAIL_NOTIFICATIONS_ENABLED
                        and anmeldelse.oprettet_af
                        and anmeldelse.oprettet_af["email"]
                        and len(anmeldelse.oprettet_af["email"]) > 0
                    ):
                        send_email(
                            f"Afgiftsanmeldelse {anmeldelse.id} er blevet afvist",
                            "admin/emails/afgiftsanmeldelse_afvist.txt",
                            html_template="admin/emails/afgiftsanmeldelse_afvist.html",
                            to=[anmeldelse.oprettet_af["email"]],
                            context={
                                "id": anmeldelse.id,
                                "status_change_reason": notat,
                                "afgiftsanmeldelse_link": f"{settings.HOST_DOMAIN}/blanket/tf10/{anmeldelse.id}",
                            },
                        )
                else:
                    self.rest_client.afgiftanmeldelse.set_status(anmeldelse_id, status)
            else:
                # Opret notat _efter_ den nye version af anmeldelsen, så vores historik-filtrering fungerer
                if notat:
                    self.rest_client.notat.create({"tekst": notat}, self.kwargs["id"])

        except HTTPError as e:
            if e.response.status_code == 404:
                raise Http404("Afgiftsanmeldelse findes ikke")
            raise
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("tf10_view", kwargs={"id": self.kwargs["id"]})


class TF10ListView(AdminLayoutBaseView, common_views.TF10ListView):
    actions_template = "admin/blanket/tf10/link.html"
    required_permissions = (
        "auth.admin",
        *common_views.TF10ListView.required_permissions,
    )
    form_class = forms.TF10SearchForm

    @cached_property
    def toldkategorier(self):
        return self.rest_client.toldkategori.list()

    def get_form_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["toldkategorier"] = self.toldkategorier
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(TF10ListView, self).get_context_data(**kwargs)
        context["title"] = "Afgiftsanmeldelser"
        context["can_create"] = TF10FormCreateView.has_permissions(request=self.request)
        context["can_view"] = TF10View.has_permissions(request=self.request)
        context["can_edit_multiple"] = TF10FormUpdateView.has_permissions(
            request=self.request
        )
        context["multiedit_url"] = reverse("tf10_edit_multiple")
        return context


class TF10FormCreateView(AdminLayoutBaseView, common_views.TF10FormCreateView):
    required_permissions = (
        "auth.admin",
        *common_views.TF10FormCreateView.required_permissions,
    )
    form_class = forms.TF10CreateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        count, users = self.rest_client.user.list(
            group="ErhvervIndberettere", limit=100000
        )
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


class TF10FormUpdateView(AdminLayoutBaseView, common_views.TF10FormUpdateView):
    form_class = forms.TF10UpdateForm  # type: ignore
    required_permissions = (
        "auth.admin",
        *common_views.TF10FormUpdateView.required_permissions,
    )

    @cached_property
    def toldkategorier(self):
        return self.rest_client.toldkategori.list()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["toldkategorier"] = self.toldkategorier
        return kwargs

    def get_context_data(self, **context):
        return super().get_context_data(
            **{
                **context,
                "admin": True,
                "gem_top": True,
            }
        )

    def status(self, item, form):
        if item.status == "afvist":
            return "ny"

    def get_initial(self):
        initial = super().get_initial()
        item = self.item
        if item:
            initial["toldkategori"] = item.toldkategori
        return initial


class TF10DeleteView(common_views.TF10FormDeleteView, AdminLayoutBaseView):
    allowed_statuses_delete = ["ny", "kladde", "afvist", "godkendt"]


class TF10HistoryListView(AdminLayoutBaseView, common_views.ListView):
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
        self.notater = {
            item.index: item
            for item in self.rest_client.notat.list(afgiftsanmeldelse=id)
        }
        count, items = self.rest_client.afgiftanmeldelse.list_history(id)
        return {"count": count, "items": items}

    def item_to_json_dict(
        self, item: Dict[str, Any], context: Dict[str, Any], index: int
    ) -> Dict[str, Any]:
        return {
            key: self.map_value(item, key, context, index)
            for key in (
                "history_username",
                "history_date",
                "notat",
                "status",
                "actions",
            )
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
        if key == "status":
            return value.capitalize()

        if value is None:
            value = ""
        return value


class TF10HistoryDetailView(
    AdminLayoutBaseView, common_views.TF10BaseView, TemplateView
):
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


class TF10EditMultipleView(AdminLayoutBaseView, FormView):
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
        except ValueError:
            return HttpResponseBadRequest("Invalid id value")
        if not self.ids:
            return HttpResponseBadRequest("Missing id value")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if len(self.ids) == 1:
            return redirect("tf10_edit", id=self.ids[0])
        return super().get(request, *args, **kwargs)

    @cached_property
    def items(self) -> List[Afgiftsanmeldelse]:
        if self.ids:
            count, items = self.rest_client.afgiftanmeldelse.list(
                id=self.ids, full=True
            )
            return items
        return []  # pragma: no cover

    @cached_property
    def fragttyper(self) -> Set[str]:
        fragttyper = set()
        for item in self.items:
            if item.fragtforsendelse and not isinstance(item.fragtforsendelse, int):
                fragttyper.add(
                    "skibsfragt"
                    if item.fragtforsendelse.forsendelsestype == Forsendelsestype.SKIB
                    else "luftfragt"
                )
            if item.postforsendelse and not isinstance(item.postforsendelse, int):
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


class AfgiftstabelListView(AdminLayoutBaseView, GetFormView):
    template_name = "admin/afgiftstabel/list.html"
    actions_template = "admin/afgiftstabel/handlinger.html"
    required_permissions = AdminLayoutBaseView.permissions_view_afgiftstabeller

    form_class = forms.AfgiftstabelSearchForm
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
        if key in ("gyldig_fra", "gyldig_til"):
            if value:
                value = datetime.fromisoformat(value)
                item[key] = value
        if key == "gældende":
            now = datetime.now(timezone.utc)
            value = (
                not item["kladde"]
                and item["gyldig_fra"] <= now
                and (item["gyldig_til"] is None or now < item["gyldig_til"])
            )
        return value


class AfgiftstabelDetailView(AdminLayoutBaseView, FormView):
    required_permissions = (
        "auth.admin",
        "sats.view_afgiftstabel",
        "sats.view_vareafgiftssats",
    )
    edit_permissions = ("sats.change_afgiftstabel",)
    delete_permissions = ("sats.delete_afgiftstabel",)
    approve_permissions = ("sats.approve_afgiftstabel",)
    template_name = "admin/afgiftstabel/view.html"
    form_class = forms.AfgiftstabelUpdateForm

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **{
                **kwargs,
                "object": self.item,
                "can_edit": (
                    self.item.kladde
                    or self.item.gyldig_fra > datetime.now(timezone.utc)
                )
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
                "can_approve_drafts": self.has_permissions(
                    request=self.request, required_permissions=self.approve_permissions
                ),
            }
        )

    def get_initial(self):
        return {
            "gyldig_fra": (
                self.item.gyldig_fra.strftime(self.form_class.format)
                if self.item.gyldig_fra
                else None
            ),
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

        # if draft-status is missing from the form, ex when users dont have permissions
        # to change it, use the current draft-status.
        tabel_draft = self.item.kladde
        if "kladde" in form.cleaned_data and form.cleaned_data["kladde"] == "":
            form.cleaned_data["kladde"] = tabel_draft

        try:
            if tabel_draft or self.item.gyldig_fra > datetime.now(timezone.utc):
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
                    [
                        header["field"]
                        for header in VareafgiftssatsSpreadsheetUtil.header_definitions
                    ],
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
        headers_pretty = [
            header["label"]
            for header in VareafgiftssatsSpreadsheetUtil.header_definitions
        ]
        if format == "xlsx":
            return SpreadsheetExport.render_xlsx(headers_pretty, rows, filename)
        if format == "csv":
            return SpreadsheetExport.render_csv(headers_pretty, rows, filename)


class AfgiftstabelCreateView(AdminLayoutBaseView, FormView):
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
        afgiftsgruppenummer_to_id: dict = {}
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


class TF5ListView(AdminLayoutBaseView, common_views.TF5ListView):
    actions_template = "admin/blanket/tf5/actions.html"
    form_class = forms.TF5SearchForm

    def get_context_data(self, **context: Dict[str, Any]) -> Dict[str, Any]:
        return super().get_context_data(
            **{
                **context,
                "title": _("Private indførselstilladelser"),
                "can_create": False,
                "can_cancel": False,
            }
        )


class TF5View(AdminLayoutBaseView, common_views.TF5View, FormView):
    form_class = forms.TF5ViewForm
    required_permissions = (
        "auth.admin",
        "anmeldelse.view_privatafgiftsanmeldelse",
    )
    payment_permissions = (
        "payment.add_payment",
        "payment.add_item",
        "payment.bank_payment",
    )
    show_notater = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "object": self.object,
                "tillægsafgift": self.object.tillægsafgift,
                "can_opret_betaling": self.can_opret_betaling,
            }
        )
        return context

    @cached_property
    def can_opret_betaling(self):
        return (
            self.has_permissions(
                request=self.request, required_permissions=self.payment_permissions
            )
            and self.object.payment_status != "paid"
        )

    def form_valid(self, form):
        anmeldelse_id = self.kwargs["id"]
        betalt = form.cleaned_data["betalt"]
        if betalt and self.can_opret_betaling:
            response = self.check_permissions(self.edit_permissions)
            if response:
                return response
            self.rest_client.payment.create(
                {
                    "declaration_id": anmeldelse_id,
                    "provider": "bank",
                }
            )
        return super().form_valid(form)


class TF5UpdateView(AdminLayoutBaseView, common_views.TF5UpdateView):
    form_class = forms.TF5Form

    def form_valid(self, form, formset):
        response = super().form_valid(form, formset)
        privatanmeldelse_id = self.kwargs["id"]
        notat = form.cleaned_data["notat"]

        # Opret notat _efter_ den nye version af anmeldelsen, så vores historik-filtrering fungerer
        if notat:
            self.rest_client.notat.create(
                {"tekst": notat}, privatafgiftsanmeldelse_id=privatanmeldelse_id
            )

        return response


class TF5LeverandørFakturaView(common_views.LeverandørFakturaView):
    required_permissions = (
        "auth.admin",
        "anmeldelse.view_privatafgiftsanmeldelse",
    )
    api = "privat_afgiftsanmeldelse"
    key = "leverandørfaktura"


class StatistikView(AdminLayoutBaseView, FormWithFormsetView):
    required_permissions = ("auth.admin",)
    form_class = forms.StatistikForm
    formset_class = forms.StatistikGruppeFormSet
    template_name = "admin/statistik.html"

    def get_formset_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_formset_kwargs()
        # The form_kwargs dict is passed as kwargs to subforms in the formset
        if "form_kwargs" not in kwargs:
            kwargs["form_kwargs"] = {}
        # Will be picked up by StatistikGruppeForm's constructor
        kwargs["form_kwargs"]["gruppe_choices"] = sorted(
            list(
                set(
                    (
                        sats.afgiftsgruppenummer
                        for sats in self.rest_client.vareafgiftssats.list()
                    )
                )
            )
        )
        return kwargs

    def form_valid(self, form, formset):
        context = super().get_context_data()

        stats = self.rest_client.statistik.list(
            **filter_dict_values(form.cleaned_data, (None, ""))
        )["items"]

        stats_by_afgiftsgruppenummer = {}
        for stat in stats:
            if stat["enhed"] in (Vareafgiftssats.Enhed.ANTAL.value,):
                stat["kvantum"] = stat["sum_antal"]
            elif stat["enhed"] in (
                Vareafgiftssats.Enhed.KILOGRAM.value,
                Vareafgiftssats.Enhed.LITER.value,
            ):
                stat["kvantum"] = Decimal(stat["sum_mængde"])
            else:
                stat["kvantum"] = None
            stats_by_afgiftsgruppenummer[stat["afgiftsgruppenummer"]] = stat

        grupperinger = []
        for subform in formset:
            gruppe = subform.cleaned_data.get("gruppe")
            if gruppe:
                gruppe_sum = sum(
                    [
                        Decimal(
                            stats_by_afgiftsgruppenummer[int(afgiftsgruppenummer)][
                                "sum_afgiftsbeløb"
                            ]
                        )
                        for afgiftsgruppenummer in gruppe
                    ]
                )
                grupperinger.append(
                    {
                        "gruppe": set([int(g) for g in gruppe]),
                        "sum_afgiftsbeløb": gruppe_sum,
                    }
                )

        context.update({"rows": stats, "grupperinger": grupperinger})
        if form.cleaned_data["download"]:
            headers = ["AFGIFTGRP", "AFGIFTSTEKST", "KVANTUM", "AFGIFT"]
            visited = set()
            grp_by_nr = {}
            if grupperinger:
                for gruppering in grupperinger:
                    for medlem in gruppering["gruppe"]:
                        grp_by_nr[medlem] = gruppering
                headers += ["GRUPPE", "GRUPPESUM"]
            rows = []
            for stat in stats:
                afgiftsgruppenummer = stat["afgiftsgruppenummer"]
                visited.add(afgiftsgruppenummer)
                row = [
                    str(afgiftsgruppenummer).zfill(3),
                    stat["vareart_da"],
                    stat["kvantum"],
                    Decimal(stat["sum_afgiftsbeløb"], Context(prec=2)),
                ]
                gruppe_data = grp_by_nr.get(afgiftsgruppenummer)
                if gruppe_data and gruppe_data["gruppe"].issubset(visited):
                    row.append(join("+", list(gruppe_data["gruppe"])))
                    row.append(gruppe_data["sum_afgiftsbeløb"])
                rows.append(row)

            daterange = format_daterange(
                form.cleaned_data["startdato"], form.cleaned_data["slutdato"]
            )
            filnavn = (
                " ".join(
                    [
                        "statistik",
                        form.cleaned_data["anmeldelsestype"] or "alle",
                        f"({daterange})",
                    ]
                )
                + ".xlsx"
            )

            return SpreadsheetExport.render_xlsx(headers, rows, filnavn, [None, 50.0])
        return self.render_to_response(context)
