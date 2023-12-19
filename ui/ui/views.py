# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
import os
from datetime import date
from functools import cached_property
from io import BytesIO
from typing import Any, Dict

from django.conf import settings
from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from requests import HTTPError
from told_common import forms as common_forms
from told_common import views as common_views

from ui import forms

from told_common.util import (  # isort: skip
    dataclass_map_to_dict,
    language,
    opt_str,
    render_pdf,
    write_pdf,
)
from told_common.view_mixins import (  # isort: skip
    FormWithFormsetView,
    HasRestClientMixin,
    PermissionsRequiredMixin,
)


class TF10FormCreateView(common_views.TF10FormCreateView):
    extend_template = "ui/layout.html"


class TF10ListView(common_views.TF10ListView):
    actions_template = "ui/tf10/actions.html"
    extend_template = "ui/layout.html"

    def get_context_data(self, **context):
        return super().get_context_data(**{**context, "can_create": True})


class TF10FormUpdateView(common_views.TF10FormUpdateView):
    extend_template = "ui/layout.html"


class TF10LeverandørFakturaView(common_views.LeverandørFakturaView):
    required_permissions = ("anmeldelse.view_afgiftsanmeldelse",)
    api = "afgiftsanmeldelse"
    key = "leverandørfaktura"


class TF5FormCreateView(
    PermissionsRequiredMixin, HasRestClientMixin, FormWithFormsetView
):
    form_class = common_forms.TF5Form
    formset_class = common_forms.TF10VareFormSet
    template_name = "told_common/tf5/form.html"
    extend_template = "ui/layout.html"
    required_permissions = (
        "anmeldelse.view_afgiftsanmeldelse",
        "anmeldelse.view_varelinje",
        "anmeldelse.add_afgiftsanmeldelse",
        "anmeldelse.add_varelinje",
        "sats.view_vareafgiftssats",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.anmeldelse_id = None

    def get_success_url(self):
        """
        Return to previous page. Make sure that the last form is displayed in the first
        row and highlight it. Also show a success message.
        """
        return (
            reverse("tf5_list")
            + "?sort=id"
            + "&order=desc"
            + f"&highlight={self.anmeldelse_id}"
        )

    def form_valid(self, form, formset):
        self.anmeldelse_id = self.rest_client.privat_afgiftsanmeldelse.create(
            {**form.cleaned_data, "indførselstilladelse": self.indførselstilladelse},
            self.request.FILES["leverandørfaktura"],
        )
        for subform in formset:
            if subform.cleaned_data:
                self.rest_client.varelinje.create(
                    subform.cleaned_data, privatafgiftsanmeldelse_id=self.anmeldelse_id
                )
        messages.add_message(
            self.request,
            messages.INFO,
            _(
                "Afgiftsanmeldelsen blev indregistreret. "
                "Blanket med nummer {id} afventer nu godkendelse."
            ).format(id=self.anmeldelse_id),
        )
        return super().form_valid(form, formset)

    @cached_property
    def toplevel_varesatser(self):
        return dict(
            filter(
                lambda pair: pair[1].overordnet is None,
                self.rest_client.varesatser_privat.items(),
            )
        )

    def get_seneste_indførselstilladelse(self, cpr: int) -> str:
        return opt_str(
            self.rest_client.privat_afgiftsanmeldelse.seneste_indførselstilladelse(cpr)
        )

    @property
    def indførselstilladelse(self):
        if self.userdata.get("indberetter_data"):
            cpr = self.userdata["indberetter_data"]["cpr"]
            return self.get_seneste_indførselstilladelse(cpr)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "varesatser": self.toplevel_varesatser,
            }
        )
        if "initial" in kwargs:
            initial = kwargs["initial"]
        else:
            initial = kwargs["initial"] = {}
        if self.userdata:
            if self.userdata.get("indberetter_data"):
                cpr = self.userdata["indberetter_data"]["cpr"]
                initial["cpr"] = cpr
            if "first_name" in self.userdata or "last_name" in self.userdata:
                initial["navn"] = " ".join(
                    filter(
                        None,
                        (
                            self.userdata.get("first_name"),
                            self.userdata.get("last_name"),
                        ),
                    )
                )
        initial["anonym"] = False
        return kwargs

    def get_formset_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_formset_kwargs()
        # The form_kwargs dict is passed as kwargs to subforms in the formset
        if "form_kwargs" not in kwargs:
            kwargs["form_kwargs"] = {}
        # Will be picked up by TF10VareForm's constructor
        kwargs["form_kwargs"]["varesatser"] = dict(
            filter(
                lambda pair: pair[1].overordnet is None,
                self.rest_client.varesatser_privat.items(),
            )
        )
        return kwargs

    def get_context_data(self, **context: Dict[str, Any]) -> Dict[str, Any]:
        context = super().get_context_data(
            **{
                **context,
                "varesatser": dataclass_map_to_dict(self.rest_client.varesatser_privat),
                "konstanter": {
                    "tillægsafgift_faktor": settings.TILLÆGSAFGIFT_FAKTOR,
                    "ekspeditionsgebyr": settings.EKSPEDITIONSGEBYR,
                },
                "extend_template": self.extend_template,
                "highlight": self.request.GET.get("highlight"),
            }
        )
        context["indførselstilladelse"] = self.indførselstilladelse
        return context


class TF5ListView(common_views.TF5ListView):
    actions_template = "ui/tf5/actions.html"

    def get_context_data(self, **context: Dict[str, Any]) -> Dict[str, Any]:
        return super().get_context_data(
            **{
                **context,
                "title": _("Mine indførselstilladelser"),
                "can_create": True,
                "can_cancel": True,
            }
        )


class TF5View(common_views.TF5View):
    extend_template = "ui/layout.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_edit = (
            self.object.status == "ny"
            and self.object.indleveringsdato > date.today()
            and self.has_permissions(
                request=self.request, required_permissions=self.edit_permissions
            )
        )
        tilladelse_eksisterer = TF5TilladelseView.exists(self.kwargs["id"])
        context.update(
            {
                "object": self.object,
                "can_edit": can_edit,
                "can_cancel": can_edit,
                "tillægsafgift": self.object.tillægsafgift,
                "can_view_tilladelse": tilladelse_eksisterer,
                "can_send_tilladelse": tilladelse_eksisterer,
            }
        )
        return context


class TF5UpdateView(common_views.TF5UpdateView):
    extend_template = "ui/layout.html"


class TF5LeverandørFakturaView(common_views.LeverandørFakturaView):
    required_permissions = ("anmeldelse.view_privatafgiftsanmeldelse",)
    api = "privat_afgiftsanmeldelse"
    key = "leverandørfaktura"


class TF5TilladelseView(PermissionsRequiredMixin, HasRestClientMixin, FormView):
    template_name = "ui/tf5/tilladelse.html"
    required_permissions = ("anmeldelse.view_privatafgiftsanmeldelse",)
    edit_permissions = ("anmeldelse.add_privatafgiftsanmeldelse",)
    form_class = forms.TF5TilladelseForm

    @cached_property
    def path(self) -> str:
        return self.id_path(self.kwargs["id"])

    @staticmethod
    def id_path(id: int) -> str:
        return os.path.join(settings.TF5_ROOT, "tilladelser", f"{id}.pdf")

    @staticmethod
    def exists(id: int) -> bool:
        return os.path.exists(TF5TilladelseView.id_path(id))

    def form_valid(self, form):
        if form.cleaned_data["opret"]:
            response = self.check_permissions(self.edit_permissions)
            if response:
                return response
            context = {"object": self.object}
            with language("kl"):
                pdfdata_kl = render_pdf("told_common/tf5/tilladelse.html", context)
            with language("da"):
                pdfdata_da = render_pdf("told_common/tf5/tilladelse.html", context)
            with self.object.leverandørfaktura.open() as faktura:
                write_pdf(self.path, BytesIO(pdfdata_kl), BytesIO(pdfdata_da), faktura)
        if form.cleaned_data["send"]:
            indberetter_data = self.object.oprettet_af["indberetter_data"]
            with open(self.path, "rb") as file:
                pdfdata = file.read()
            self.rest_client.eboks.create(
                {
                    "cpr": indberetter_data.get("cpr"),
                    "cvr": indberetter_data.get("cvr"),
                    "titel": "Indførselstilladelse",
                    "pdf": pdfdata,
                    "privat_afgiftsanmeldelse_id": self.object.id,
                }
            )
        return redirect(self.request.GET.get("next") or reverse_lazy("tf5_list"))

    def get(self, request, *args, **kwargs):
        self.object  # Vil kaste 404 hvis man ikke har adgang til anmeldelsen
        return FileResponse(open(self.path, "rb"))

    @cached_property
    def object(self):
        id = self.kwargs["id"]
        try:
            anmeldelse = self.rest_client.privat_afgiftsanmeldelse.get(
                id,
                include_varelinjer=True,
            )
        except HTTPError as e:
            if e.response.status_code == 404:
                raise Http404("Afgiftsanmeldelse findes ikke")
            raise
        return anmeldelse
