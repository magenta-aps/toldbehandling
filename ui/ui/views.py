# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
import dataclasses
import os
from datetime import date
from functools import cached_property
from io import BytesIO
from typing import Any, Dict

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, RedirectView, TemplateView, View
from requests import HTTPError
from told_common import forms as common_forms
from told_common import views as common_views
from told_common.util import (
    dataclass_map_to_dict,
    language,
    opt_str,
    render_pdf,
    write_pdf,
)
from told_common.view_mixins import (
    FormWithFormsetView,
    HasRestClientMixin,
    LoginRequiredMixin,
    PermissionsRequiredMixin,
)

from ui import forms


class UiViewMixin:
    def get_context_data(self, **context):
        return super().get_context_data(
            **{
                **context,
                "can_list_tf5": TF5ListView.has_permissions(request=self.request),
                "can_list_tf10": TF10ListView.has_permissions(request=self.request),
            }
        )


class IndexView(LoginRequiredMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        if self.userdata.get("indberetter_data", {}).get("cvr"):
            return reverse("tf10_list")
        return reverse("tf5_list")


class TF10FormCreateView(UiViewMixin, common_views.TF10FormCreateView):
    extend_template = "ui/layout.html"


class TF10ListView(UiViewMixin, common_views.TF10ListView):
    actions_template = "ui/tf10/actions.html"
    extend_template = "ui/layout.html"

    def get_context_data(self, **context):
        return super().get_context_data(**{**context, "can_create": True})


class TF10FormUpdateView(UiViewMixin, common_views.TF10FormUpdateView):
    extend_template = "ui/layout.html"


class TF10LeverandørFakturaView(UiViewMixin, common_views.LeverandørFakturaView):
    required_permissions = ("anmeldelse.view_afgiftsanmeldelse",)
    api = "afgiftsanmeldelse"
    key = "leverandørfaktura"


class TF5FormCreateView(
    PermissionsRequiredMixin, HasRestClientMixin, UiViewMixin, FormWithFormsetView
):
    form_class = common_forms.TF5Form
    formset_class = common_forms.TF10VareFormSet
    template_name = "told_common/tf5/form.html"
    extend_template = "ui/layout.html"
    required_permissions = (
        "anmeldelse.view_privatafgiftsanmeldelse",
        "anmeldelse.view_varelinje",
        "anmeldelse.add_privatafgiftsanmeldelse",
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
        if form.cleaned_data["betal"]:
            return redirect(
                reverse("tf5_payment_checkout", kwargs={"id": self.anmeldelse_id})
            )
        messages.add_message(
            self.request,
            messages.INFO,
            _(
                "Afgiftsanmeldelsen blev indregistreret. "
                "Blanket med nummer {id} afventer nu betaling."
            ).format(id=self.anmeldelse_id),
        )
        return super().form_valid(form, formset)

    @cached_property
    def toplevel_varesatser(self):
        dato = date.today()
        if self.request.POST:
            if "indleveringsdato" in self.request.POST:
                dato = date.fromisoformat(self.request.POST["indleveringsdato"])
        return dict(
            filter(
                lambda pair: pair[1].overordnet is None,
                self.rest_client.varesatser_fra(dato, synlig_privat=True).items(),
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
                initial["cpr"] = str(cpr).zfill(10)
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
        kwargs["form_kwargs"]["varesatser"] = self.toplevel_varesatser
        return kwargs

    def get_context_data(self, **context: Dict[str, Any]) -> Dict[str, Any]:
        context = super().get_context_data(
            **{
                **context,
                "konstanter": {
                    "tillægsafgift_faktor": settings.TILLÆGSAFGIFT_FAKTOR,
                    "ekspeditionsgebyr": settings.EKSPEDITIONSGEBYR,
                },
                "extend_template": self.extend_template,
                "highlight": self.request.GET.get("highlight"),
                "varesatser": dataclass_map_to_dict(
                    self.rest_client.varesatser_all(
                        filter_afgiftstabel={"gyldig_til__gte": date.today()},
                        filter_varesats={"synlig_privat": True},
                    )
                ),
                "afgiftstabeller": [
                    dataclasses.asdict(item)
                    for item in self.rest_client.afgiftstabel.list(
                        gyldig_til__gte=date.today(), kladde=False
                    )
                ],
            }
        )
        context["indførselstilladelse"] = self.indførselstilladelse
        return context


class TF5ListView(UiViewMixin, common_views.TF5ListView):
    actions_template = "ui/tf5/actions.html"
    extend_template = "ui/layout.html"

    def get_context_data(self, **context: Dict[str, Any]) -> Dict[str, Any]:
        return super().get_context_data(
            **{
                **context,
                "title": _("Mine indførselstilladelser"),
                "can_create": True,
                "can_cancel": True,
            }
        )


class TF5View(UiViewMixin, common_views.TF5View):
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


class TF5UpdateView(UiViewMixin, common_views.TF5UpdateView):
    extend_template = "ui/layout.html"


class TF5LeverandørFakturaView(UiViewMixin, common_views.LeverandørFakturaView):
    required_permissions = ("anmeldelse.view_privatafgiftsanmeldelse",)
    api = "privat_afgiftsanmeldelse"
    key = "leverandørfaktura"


class TF5TilladelseView(
    PermissionsRequiredMixin, HasRestClientMixin, UiViewMixin, FormView
):
    template_name = "ui/tf5/tilladelse.html"
    required_permissions = ("anmeldelse.view_privatafgiftsanmeldelse",)
    edit_permissions = ("anmeldelse.add_privatafgiftsanmeldelse",)
    form_class = forms.TF5TilladelseForm

    @cached_property
    def path(self) -> str:
        return self.id_path(self.kwargs["id"])

    @staticmethod
    def id_path(id: int) -> str:
        return os.path.join(settings.TF5_ROOT, f"{id}.pdf")

    @staticmethod
    def exists(id: int) -> bool:
        return os.path.exists(TF5TilladelseView.id_path(id))

    def form_valid(self, form):
        if form.cleaned_data["opret"]:
            response = self.check_permissions(self.edit_permissions)
            if response:
                return response

            if self.object.payment_status != "paid":
                raise PermissionDenied("tf5 payment not paid")

            context = {"object": self.object}
            pdfdata = []
            for language_code in ("kl", "da"):
                with language(language_code):
                    pdfdata.append(
                        BytesIO(render_pdf("ui/tf5/tilladelse.html", context=context))
                    )
            for language_code in ("kl", "da"):
                with language(language_code):
                    pdfdata.append(
                        BytesIO(
                            render_pdf(
                                "told_common/tf5/view.html",
                                context={
                                    **context,
                                    "extend_template": "ui/print.html",
                                    "tillægsafgift": self.object.tillægsafgift,
                                    "can_create_tilladelse": False,
                                    "printing": True,
                                },
                                stylesheets=[
                                    "/static/bootstrap/bootstrap.min.css",
                                    "/static/toldbehandling/css/style.css",
                                    "/static/toldbehandling/css/pdfprint.css",
                                ],
                            )
                        )
                    )
            with self.object.leverandørfaktura.open() as faktura:
                pdfdata.append(faktura)
                write_pdf(self.path, *pdfdata)

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


class TF5PaymentCheckoutView(
    PermissionsRequiredMixin,
    HasRestClientMixin,
    common_views.CustomLayoutMixin,
    UiViewMixin,
    TemplateView,
):
    extend_template = "ui/layout.html"
    template_name = "ui/tf5/payment/checkout.html"

    required_permissions = (
        "payment.view_payment",
        "payment.add_payment",
    )

    def get_context_data(self, **kwargs):
        """Add the declaration and payment to the context

        If the payment does not exist, it will be created.

        IMPORTANT!
        NETs use the lowest monetary unit for the given currency. For DKK, this is
        "øre", which means we need to use a "currency multiplier" of 100 to get the
        correct value.
        ref: https://developer.nexigroup.com/nexi-checkout/en-EU/api/#currency-and-amount  # noqa: E501

        Raises:
            Exception: If the declaration or payment could not be found or created
        """
        context = super().get_context_data(**kwargs)

        payment = self.rest_client.payment.create(
            data={"declaration_id": int(self.kwargs["id"])}
        )

        if not payment:
            raise Exception("Betaling kunne ikke findes eller oprettes")

        context["payment"] = payment
        context["nets_checkout_key"] = settings.PAYMENT_PROVIDER_NETS_CHECKOUT_KEY
        return context


class TF5PaymentDetailsView(
    PermissionsRequiredMixin,
    HasRestClientMixin,
    common_views.CustomLayoutMixin,
    UiViewMixin,
    TemplateView,
):
    extend_template = "ui/layout.html"
    template_name = "ui/tf5/payment/details.html"

    required_permissions = ("payment.view_payment",)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment = self.rest_client.payment.get_by_declaration(int(self.kwargs["id"]))
        if not payment:
            raise ObjectDoesNotExist("Betaling kunne ikke findes")

        context["payment"] = payment
        return context


class TF5PaymentRefreshView(
    PermissionsRequiredMixin, HasRestClientMixin, UiViewMixin, View
):
    async def post(self, request, *args, **kwargs):
        payment_refreshed = self.rest_client.payment.refresh(int(self.kwargs["id"]))
        return JsonResponse({"payment_refreshed": payment_refreshed})
