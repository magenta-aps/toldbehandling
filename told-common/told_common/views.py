# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
import dataclasses
import json
import logging
import os
from datetime import date
from functools import cached_property
from typing import Any, Callable, Dict, Iterable, List, Optional
from urllib.parse import unquote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.exceptions import ObjectDoesNotExist
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import redirect
from django.template import loader
from django.template.response import TemplateResponse
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import FormView, RedirectView, TemplateView
from django_stubs_ext import StrPromise
from requests import HTTPError
from told_common import forms
from told_common.data import (
    Afgiftsanmeldelse,
    Forsendelsestype,
    PrivatAfgiftsanmeldelse,
    Vareafgiftssats,
)
from told_common.rest_client import RestClient
from told_common.util import (
    JSONEncoder,
    dataclass_map_to_dict,
    lenient_get,
    multivaluedict_to_querydict,
    tf5_common_context,
)
from told_common.view_mixins import (
    CustomLayoutMixin,
    FormWithFormsetView,
    HasRestClientMixin,
    LoginRequiredMixin,
    PermissionsRequiredMixin,
    PreventDoubleSubmitMixin,
    TF5Mixin,
)

log = logging.getLogger(__name__)


class LoginView(FormView):
    form_class = forms.LoginForm
    template_name = "told_common/login.html"

    def get_success_url(self):
        next = self.request.GET.get("back") or self.request.GET.get(REDIRECT_FIELD_NAME)
        if next:
            return next

    def form_valid(self, form):
        form.token.save(self.request, save_refresh_token=True)
        userdata = RestClient(form.token).user.this()
        self.request.session["user"] = userdata
        return super().form_valid(form)


class LogoutView(RedirectView):
    pattern_name = "login"

    def get(self, request, *args, **kwargs):
        for key in ("access_token", "refresh_token", "user", "twofactor_authenticated"):
            if key in request.session:
                del request.session[key]
        return super().get(request, *args, **kwargs)


class RestView(LoginRequiredMixin, HasRestClientMixin, View):
    def get(self, request, *args, **kwargs) -> JsonResponse:
        return JsonResponse(self.rest_client.get(kwargs["path"], request.GET))

    def patch(self, request, *args, **kwargs) -> JsonResponse:
        return JsonResponse(
            self.rest_client.patch(
                kwargs["path"], json.loads(request.body.decode("utf-8"))
            )
        )


class FileView(LoginRequiredMixin, HasRestClientMixin, View):
    def get(self, request, *args, **kwargs):
        # Vil kaste 404 hvis id ikke findes
        object = self.rest_client.get(f"{self.api}/{kwargs['id']}")
        # settings.MEDIA_ROOT er monteret i Docker så det deles mellem
        # containerne REST og UI.
        # Derfor kan vi læse filer der er skrevet af den anden container
        path = object[self.key]
        if not path:
            raise Http404
        path = os.path.join(settings.MEDIA_ROOT, unquote(path).lstrip("/"))
        if not os.path.exists(path):
            raise Http404
        return FileResponse(open(path, "rb"))


class LeverandørFakturaView(PermissionsRequiredMixin, FileView):
    required_permissions: Iterable[str] = ("anmeldelse.view_afgiftsanmeldelse",)
    api = "afgiftsanmeldelse"
    key = "leverandørfaktura"


class FragtbrevView(PermissionsRequiredMixin, FileView):
    required_permissions = ("forsendelse.view_fragtforsendelse",)
    api = "fragtforsendelse"
    key = "fragtbrev"


class TF10FormCreateView(
    PermissionsRequiredMixin,
    HasRestClientMixin,
    PreventDoubleSubmitMixin,
    FormWithFormsetView,
):
    form_class: Any = forms.TF10Form
    formset_class = forms.TF10VareFormSet
    template_name = "told_common/tf10/form.html"
    extend_template = "told_common/layout.html"
    required_permissions: Iterable[str] = (
        "aktør.view_afsender",
        "aktør.view_modtager",
        "aktør.add_afsender",
        "aktør.add_modtager",
        "forsendelse.view_postforsendelse",
        "forsendelse.view_fragtforsendelse",
        "forsendelse.add_postforsendelse",
        "forsendelse.add_fragtforsendelse",
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
            reverse("tf10_list")
            + "?sort=id"
            + "&order=desc"
            + f"&highlight={self.anmeldelse_id}"
        )

    def form_valid(self, form, formset):
        afsender_id = self.rest_client.afsender.get_or_create(form.cleaned_data)
        modtager_id = self.rest_client.modtager.get_or_create(form.cleaned_data)
        postforsendelse_id = self.rest_client.postforsendelse.create(form.cleaned_data)

        fragtfil = form.cleaned_data.get("fragtbrev")
        if fragtfil:
            log.info(
                "Bruger '%s' opretter TF10 med fragtbrev %s (%s bytes) (pid %d)",
                self.userdata["username"],
                fragtfil.name,
                fragtfil.size,
                os.getpid(),
            )
        else:
            log.info(
                "Bruger '%s' opretter TF10 uden at sætte fragtbrev (pid %d)",
                self.userdata["username"],
                os.getpid(),
            )

        fragtforsendelse_id = self.rest_client.fragtforsendelse.create(
            form.cleaned_data, form.cleaned_data.get("fragtbrev")
        )
        leverandørfakturafil = form.cleaned_data.get("leverandørfaktura")
        if leverandørfakturafil:
            log.info(
                "Bruger '%s' opretter TF10 med leverandørfaktura %s (%s bytes)",
                self.userdata["username"],
                leverandørfakturafil.name,
                leverandørfakturafil.size,
            )
        else:
            log.info(
                "Bruger '%s' opretter TF10 uden at sætte leverandørfaktura",
                self.userdata["username"],
            )

        self.anmeldelse_id = self.rest_client.afgiftanmeldelse.create(
            form.cleaned_data,
            form.cleaned_data.get("leverandørfaktura"),
            afsender_id,
            modtager_id,
            postforsendelse_id,
            fragtforsendelse_id,
        )
        log.info("TF10 %d oprettet", self.anmeldelse_id)
        for subform in formset:
            if subform.cleaned_data:
                self.rest_client.varelinje.create(
                    {**subform.cleaned_data, "kladde": form.cleaned_data["kladde"]},
                    self.anmeldelse_id,
                )

        # Opret notat _efter_ den nye version af anmeldelsen,
        # så vores historik-filtrering fungerer
        notat = form.cleaned_data["notat"]
        if notat:
            self.rest_client.notat.create({"tekst": notat}, self.anmeldelse_id)
        if form.cleaned_data["kladde"]:
            messages.add_message(
                self.request,
                messages.INFO,
                _("Afgiftsanmeldelsen med nummer {id} blev gemt som kladde.").format(
                    id=self.anmeldelse_id
                ),
            )
        else:
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
    def varesatser(self):
        return self.rest_client.varesatser_all()

    @cached_property
    def toplevel_current_varesatser(self):
        dato = date.today()
        if self.request.POST and "afgangsdato" in self.request.POST:
            try:
                dato = date.fromisoformat(self.request.POST["afgangsdato"])
            except ValueError:
                log.warning(
                    "Could not parse input date", self.request.POST["afgangsdato"]
                )
        return dict(
            filter(
                lambda pair: pair[1].overordnet is None,
                self.rest_client.varesatser_fra(dato).items(),
            )
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "fragtbrev_required": False,
                "varesatser": self.toplevel_current_varesatser,
            }
        )
        return kwargs

    def get_formset_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_formset_kwargs()
        # The form_kwargs dict is passed as kwargs to subforms in the formset
        if "form_kwargs" not in kwargs:
            kwargs["form_kwargs"] = {}
        # Will be picked up by TF10VareForm's constructor
        kwargs["form_kwargs"]["varesatser"] = self.toplevel_current_varesatser
        return kwargs

    def get_context_data(self, **context) -> Dict[str, Any]:
        context = super().get_context_data(
            **{
                **context,
                "varesatser": dataclass_map_to_dict(self.varesatser),
                "afgiftstabeller": [
                    dataclasses.asdict(item)
                    for item in self.rest_client.afgiftstabel.list(kladde=False)
                ],
                "extend_template": self.extend_template,
                "highlight": self.request.GET.get("highlight"),
                "kan_ændre_kladde": True,
            }
        )

        context["indberetter_data"] = (
            self.userdata["indberetter_data"]
            if "indberetter_data" in self.userdata
            and isinstance(self.userdata["indberetter_data"], dict)
            else None
        )

        return context


class TF10FormUpdateView(
    PermissionsRequiredMixin,
    HasRestClientMixin,
    CustomLayoutMixin,
    PreventDoubleSubmitMixin,
    FormWithFormsetView,
):
    required_permissions: Iterable[str] = (
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
        "forsendelse.change_postforsendelse",
        "forsendelse.change_fragtforsendelse",
    )
    form_class = forms.TF10Form
    formset_class = forms.TF10VareFormSet
    template_name = "told_common/tf10/form.html"
    extend_template = "told_common/layout.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.anmeldelse_id = None

    def check_item(self):
        if self.item.status not in ("ny", "afvist", "kladde"):
            return TemplateResponse(
                request=self.request,
                template="told_common/access_denied.html",
                headers={"Cache-Control": "no-cache"},
                status=403,
            )

    def get(self, request, *args, **kwargs):
        response = self.check_item()
        if response:
            return response
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        response = self.check_item()
        if response:
            return response
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        """
        Return to previous page. Highlight the updated form and display a success msg.
        """
        if self.request.GET.get("back") == "view" and self.anmeldelse_id is not None:
            return reverse("tf10_view", kwargs={"id": self.anmeldelse_id})
        return reverse("tf10_list") + f"?highlight={self.anmeldelse_id}"

    def form_valid(self, form, formset):
        self.anmeldelse_id = self.item.id
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

        fragtfil = form.cleaned_data.get("fragtbrev")
        if fragtfil:
            log.info(
                "Bruger '%s' opdaterer TF10 %d med fragtbrev %s (%d bytes)",
                self.userdata["username"],
                self.anmeldelse_id,
                fragtfil.name,
                fragtfil.size,
            )
        else:
            log.info(
                "Bruger '%s' opdaterer TF10 %d uden at sætte fragtbrev",
                self.userdata["username"],
                self.anmeldelse_id,
            )

        fragtforsendelse_id = (
            self.item.fragtforsendelse.id if self.item.fragtforsendelse else None
        )
        if fragtforsendelse_id:
            fragtforsendelse_id = self.rest_client.fragtforsendelse.update(
                fragtforsendelse_id,
                form.cleaned_data,
                form.cleaned_data.get("fragtbrev"),
                self.item.fragtforsendelse,
            )
        else:
            # Håndterer oprettelse af ny
            fragtforsendelse_id = self.rest_client.fragtforsendelse.create(
                form.cleaned_data, form.cleaned_data.get("fragtbrev")
            )

        leverandørfakturafil = form.cleaned_data.get("leverandørfaktura")
        if leverandørfakturafil:
            log.info(
                "Bruger '%s' opdaterer TF10 %d med leverandørfaktura %s (%d bytes)",
                self.userdata["username"],
                self.anmeldelse_id,
                leverandørfakturafil.name,
                leverandørfakturafil.size,
            )
        else:
            log.info(
                "Bruger '%s' opdaterer TF10 %d uden at sætte leverandørfaktura",
                self.userdata["username"],
                self.anmeldelse_id,
            )
        self.rest_client.afgiftanmeldelse.update(
            self.anmeldelse_id,
            form.cleaned_data,
            form.cleaned_data.get("leverandørfaktura"),
            afsender_id,
            modtager_id,
            postforsendelse_id,
            fragtforsendelse_id,
            self.item,
            force_write=True,
            status=self.status(self.item, form),
        )
        log.info("TF10 %d opdateret", self.anmeldelse_id)

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

        # Opret notat _efter_ den nye version af anmeldelsen,
        # så vores historik-filtrering fungerer
        notat = form.cleaned_data["notat"]
        if notat:
            self.rest_client.notat.create({"tekst": notat}, self.anmeldelse_id)

        if self.request.GET.get("back") != "view":
            messages.add_message(
                self.request,
                messages.INFO,
                _("Afgiftsanmeldelsen med nummer {id} blev opdateret").format(
                    id=self.anmeldelse_id
                ),
            )

        return super().form_valid(form, formset)

    def status(self, item, form):
        return None  # override in subclasses. None means "no change"

    @cached_property
    def varesatser(self):
        return self.rest_client.varesatser_all()

    @cached_property
    def toplevel_current_varesatser(self):
        dato = self.item.afgangsdato or date.today()
        if self.request.POST and "afgangsdato" in self.request.POST:
            try:
                dato = date.fromisoformat(self.request.POST["afgangsdato"])
            except ValueError:
                log.warning(
                    "Could not parse input date", self.request.POST["afgangsdato"]
                )
        return dict(
            filter(
                lambda pair: pair[1].overordnet is None,
                self.rest_client.varesatser_fra(dato).items(),
            )
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                # Påkrævet hvis vi ikke allerede har én
                "leverandørfaktura_required": not self.item.leverandørfaktura,
                # Hvis vi allerede har en fragtforsendelse, har vi også et
                # fragtbrev, og det er ikke påkrævet at formularen indeholder ét
                "fragtbrev_required": False,
                "varesatser": self.toplevel_current_varesatser,
            }
        )
        return kwargs

    def get_formset_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_formset_kwargs()
        # The form_kwargs dict is passed as kwargs to subforms in the formset
        if "form_kwargs" not in kwargs:
            kwargs["form_kwargs"] = {}
        # Will be picked up by TF10VareForm's constructor
        kwargs["form_kwargs"]["varesatser"] = self.toplevel_current_varesatser
        initial = []
        for item in self.item.varelinjer or []:
            itemdict = dataclasses.asdict(item)
            # Dropdown skal bruge id'er, ikke objekter
            if itemdict["vareafgiftssats"]:
                vareafgiftssats_id = itemdict["vareafgiftssats"]["id"]
                if vareafgiftssats_id not in self.toplevel_current_varesatser:
                    afgiftsgruppenummer = itemdict["vareafgiftssats"][
                        "afgiftsgruppenummer"
                    ]
                    for vareafgiftssats in self.toplevel_current_varesatser.values():
                        if vareafgiftssats.afgiftsgruppenummer == afgiftsgruppenummer:
                            vareafgiftssats_id = vareafgiftssats.id
                            break
                itemdict["vareafgiftssats"] = vareafgiftssats_id
            initial.append(itemdict)
        kwargs["initial"] = initial
        return kwargs

    def get_context_data(self, **context: Dict[str, Any]) -> Dict[str, Any]:
        return super().get_context_data(
            **{
                **context,
                "vis_notater": True,
                "varesatser": dataclass_map_to_dict(self.varesatser),
                "afgiftstabeller": [
                    dataclasses.asdict(item)
                    for item in self.rest_client.afgiftstabel.list(kladde=False)
                ],
                "item": self.item,
                "notater": self.rest_client.notat.list(
                    afgiftsanmeldelse=self.kwargs["id"]
                ),
                "kan_ændre_kladde": self.item.status == "kladde",
                "indberetter_data": {
                    "cvr": (
                        lenient_get(self.item.indberetter, "indberetter_data", "cvr")
                        if self.item.indberetter
                        else None
                    )
                },
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
            initial["kladde"] = item.status == "kladde"
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
            initial["betales_af"] = item.betales_af
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
            if item.fuldmagtshaver:
                initial["fuldmagtshaver"] = getattr(item.fuldmagtshaver, "cvr")
            initial["tf3"] = item.tf3
        return initial


class TF10FormDeleteView(
    PermissionsRequiredMixin,
    HasRestClientMixin,
    CustomLayoutMixin,
    TemplateView,
):
    template_name = "told_common/tf10/delete.html"
    required_permissions = (
        "anmeldelse.view_afgiftsanmeldelse",
        "anmeldelse.delete_afgiftsanmeldelse",
    )
    allowed_statuses_delete = ["ny", "kladde"]

    def get(self, request, *args, **kwargs):
        if not self.item:
            raise ObjectDoesNotExist("Afgiftsanmeldelse kunne ikke findes")

        if self.item.status not in self.allowed_statuses_delete:
            return TemplateResponse(
                request=self.request,
                status=403,
                headers={"Cache-Control": "no-cache"},
                template="told_common/access_denied.html",
                context={"invalid_status": self.item.status},
            )

        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        declaration_id = int(self.kwargs["id"])
        resp = self.rest_client.afgiftanmeldelse.delete(declaration_id)
        if resp["success"] is not True:
            raise Exception(f"Afgiftsanmeldelse {declaration_id} kunne ikke slettes")

        return redirect(reverse_lazy("tf10_list"))

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **{
                **kwargs,
                "declaration": self.item,
            }
        )

    @cached_property
    def item(self):
        return self.rest_client.afgiftanmeldelse.get(
            self.kwargs["id"],
            full=True,
        )


class ListView(FormView):
    list_size: int = 20
    form_class = forms.PaginateForm
    select_template: Optional[str] = None

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

    def store_search(self, search_data: dict):
        if "list_search" not in self.request.session:
            self.request.session["list_search"] = {}
        search_data = dict(search_data)
        search_data.pop("json", None)
        self.request.session["list_search"][self.request.path] = search_data
        self.request.session.modified = True

    def load_search(self):
        return multivaluedict_to_querydict(
            lenient_get(self.request.session, "list_search", self.request.path)
        )

    def item_to_json_dict(
        self, item: Dict[str, Any], context: Dict[str, Any], index: int
    ) -> Dict[str, Any]:
        return {**item, "select": item["id"]}

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

    def get_initial(self) -> Dict[str, str | List[str]]:
        return {}

    def get_form_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_form_kwargs()
        query_dict = self.request.GET.copy()
        query_dict.pop("highlight", None)
        if not query_dict:
            query_dict = self.load_search()
        else:
            self.store_search(query_dict)
        if not query_dict:
            for key, value in self.get_initial().items():
                if isinstance(value, list):
                    query_dict.setlist(key, value)
                else:
                    query_dict[key] = value
        kwargs["data"] = query_dict
        return kwargs


class TF10ListView(
    PermissionsRequiredMixin, HasRestClientMixin, CustomLayoutMixin, ListView
):
    required_permissions: Iterable[str] = (
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
                "title": _("Mine afgiftsanmeldelser"),
                "highlight": self.request.GET.get("highlight"),
                "can_edit": TF10FormUpdateView.has_permissions(request=self.request),
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
                "forbindelsesnummer",
                "status",
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
        if key == "status":
            return _(value.capitalize())
        return value

    def get_form_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_form_kwargs()

        # Will be picked up by TF10SearchForm's constructor
        kwargs["varesatser"] = dict(
            filter(
                lambda pair: pair[1].overordnet is None,
                self.rest_client.varesatser.items(),
            )
        )
        kwargs["afsendere"] = {
            item[1]["id"]: item[1] for item in self.rest_client.afsendere.items()
        }
        kwargs["modtagere"] = {
            item[1]["id"]: item[1] for item in self.rest_client.modtagere.items()
        }
        kwargs["permissions"] = set(self.userdata.get("permissions") or [])
        return kwargs


class TF10BaseView:
    rest_client: RestClient

    def get_subsatser(self, parent_id: int) -> List[Vareafgiftssats]:
        return self.rest_client.vareafgiftssats.list(overordnet=parent_id)


class TF10View(TF10BaseView, TemplateView):
    required_permissions: Iterable[str] = (
        "aktør.view_afsender",
        "aktør.view_modtager",
        "forsendelse.view_postforsendelse",
        "forsendelse.view_fragtforsendelse",
        "anmeldelse.view_afgiftsanmeldelse",
        "anmeldelse.view_varelinje",
        "sats.view_vareafgiftssats",
    )
    edit_permissions = ("anmeldelse.change_afgiftsanmeldelse",)
    extend_template = "told_common/layout.html"
    template_name = "told_common/tf10/view.html"
    has_permissions: Callable

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        anmeldelse: Afgiftsanmeldelse = self.object

        return super().get_context_data(
            **{
                **kwargs,
                "object": anmeldelse,
                "can_edit": self.has_permissions(
                    request=self.request, required_permissions=self.edit_permissions
                )
                and anmeldelse.status in ("ny", "kladde", "afvist"),
                "extend_template": self.extend_template,
                "indberettere": self.get_indberettere(anmeldelse),
            }
        )

    def get_initial(self):
        initial = super().get_initial()
        if self.object.toldkategori:
            initial["toldkategori"] = self.object.toldkategori
        if self.object.modtager.stedkode:
            initial["modtager_stedkode"] = self.object.modtager.stedkode
        return initial

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
                raise Http404(_("Afgiftsanmeldelse findes ikke"))
            raise
        return anmeldelse

    def get_indberettere(self, anmeldelse: Afgiftsanmeldelse):
        reportees = []
        if anmeldelse.oprettet_af:
            reportees.append(
                TF10View.reportee_from_user_dict(
                    _("Oprettet af"), anmeldelse.oprettet_af
                )
            )

        if anmeldelse.oprettet_på_vegne_af:
            reportees.append(
                TF10View.reportee_from_user_dict(
                    _("Oprettet på vegne af"), anmeldelse.oprettet_på_vegne_af
                )
            )

        if anmeldelse.fuldmagtshaver:
            reportees.append(
                {
                    "type": _("Fuldmagtshaver"),
                    "navn": anmeldelse.fuldmagtshaver.navn,
                    "cpr_cvr": {
                        "cpr": None,
                        "cvr": str(anmeldelse.fuldmagtshaver.cvr).zfill(8),
                    },
                }
            )

        return reportees

    @staticmethod
    def reportee_from_user_dict(type_label: StrPromise, user_dict: dict):
        cvr = lenient_get(user_dict, "indberetter_data", "cvr")
        return {
            "type": type_label,
            "navn": f"{user_dict['first_name']} {user_dict['last_name']}",
            "cvr": str(cvr).zfill(8) if cvr else None,
        }


class TF5View(
    PermissionsRequiredMixin, HasRestClientMixin, CustomLayoutMixin, TF5Mixin, FormView
):
    required_permissions: Iterable[str] = (
        "anmeldelse.view_privatafgiftsanmeldelse",
        "anmeldelse.view_varelinje",
        "sats.view_vareafgiftssats",
    )
    edit_permissions = ("anmeldelse.change_privatafgiftsanmeldelse",)

    template_name = "told_common/tf5/view.html"
    form_class = forms.TF5ViewForm
    show_notater = False

    def get_subsatser(self, parent_id: int) -> List[Vareafgiftssats]:
        return self.rest_client.vareafgiftssats.list(overordnet=parent_id)

    def get_context_data(self, **kwargs):
        can_edit = (
            self.object.status == "ny"
            and self.object.indleveringsdato > date.today()
            and self.has_permissions(
                request=self.request, required_permissions=self.edit_permissions
            )
        )
        return super().get_context_data(
            **{
                **kwargs,
                **tf5_common_context(),
                "object": self.object,
                "tillægsafgift": self.object.tillægsafgift,
                # Opret en path i admin/urls.py ved navn "tf5_tilladelse"
                # hvis denne sættes til True
                "can_create_tilladelse": False,
                "show_notater": self.show_notater,
                "can_opret_betaling": False,
                "can_cancel": can_edit,
                "can_edit": can_edit,
            }
        )

    def form_valid(self, form):
        anmeldelse_id = self.kwargs["id"]
        annulleret = form.cleaned_data["annulleret"]
        notat = form.cleaned_data["notat1"]

        try:
            if annulleret:
                # Yderligere tjek for om brugeren må ændre noget.
                # Vi kan have en situation hvor brugeren må se siden
                # men ikke submitte formularen
                response = self.check_permissions(self.edit_permissions)
                if response:
                    return response
                self.rest_client.privat_afgiftsanmeldelse.annuller(anmeldelse_id)

            # Opret notat _efter_ den nye version af anmeldelsen,
            # så vores historik-filtrering fungerer
            if notat:
                self.rest_client.notat.create({"tekst": notat}, self.kwargs["id"])

        except HTTPError as e:
            if e.response.status_code == 404:
                raise Http404(_("Afgiftsanmeldelse findes ikke"))
            raise
        return redirect(reverse("tf5_view", kwargs={"id": anmeldelse_id}))

    @cached_property
    def object(self):
        id = self.kwargs["id"]
        try:
            anmeldelse = self.rest_client.privat_afgiftsanmeldelse.get(
                id,
                include_notater=self.show_notater,
                include_varelinjer=True,
            )
        except HTTPError as e:
            if e.response.status_code == 404:
                raise Http404(_("Afgiftsanmeldelse findes ikke"))
            raise
        return anmeldelse


class TF5ListView(PermissionsRequiredMixin, HasRestClientMixin, TF5Mixin, ListView):
    required_permissions = (
        "anmeldelse.view_privatafgiftsanmeldelse",
        "anmeldelse.view_varelinje",
    )
    select_template = "told_common/tf5/select.html"
    template_name = "told_common/tf5/list.html"
    extend_template = "told_common/layout.html"
    form_class = forms.TF5SearchForm
    list_size = 20

    def get_items(self, search_data: Dict[str, Any]):
        count, items = self.rest_client.privat_afgiftsanmeldelse.list(**search_data)
        return {"count": count, "items": items}

    def get_context_data(self, **context: Dict[str, Any]) -> Dict[str, Any]:
        return super().get_context_data(
            **{
                **context,
                **tf5_common_context(),
                "highlight": self.request.GET.get("highlight"),
                "extend_template": self.extend_template,
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
                "oprettet",
                "indleveringsdato",
                "leverandørfaktura_nummer",
                "status",
                "actions",
            )
        }

    def map_value(self, item, key, context):
        if key == "actions":
            return loader.render_to_string(
                self.actions_template,
                {
                    "item": item,
                    "can_edit": item.indleveringsdato > date.today(),
                    **context,
                },
                self.request,
            )
        if key == "select":
            return loader.render_to_string(
                self.select_template,
                {"item": item, **context},
                self.request,
            )
        value = getattr(item, key)
        if key == "status":
            return _(value.capitalize())

        if value is not None and key in ("oprettet", "indleveringsdato"):
            return value.strftime("%d-%m-%Y")

        return value

    def get_form_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_form_kwargs()

        # Will be picked up by TF10SearchForm's constructor
        kwargs["varesatser"] = dict(
            filter(
                lambda pair: pair[1].overordnet is None,
                self.rest_client.varesatser_privat.items(),
            )
        )
        kwargs["initial"] = {}
        return kwargs


class TF5UpdateView(
    PermissionsRequiredMixin,
    HasRestClientMixin,
    TF5Mixin,
    PreventDoubleSubmitMixin,
    FormWithFormsetView,
):
    extend_template: str
    required_permissions = (
        "anmeldelse.view_privatafgiftsanmeldelse",
        "anmeldelse.view_varelinje",
        "anmeldelse.change_privatafgiftsanmeldelse",
        "anmeldelse.change_varelinje",
    )
    form_class = forms.TF5Form
    formset_class = forms.TF10VareFormSet
    template_name = "told_common/tf5/form.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.anmeldelse_id = None

    def get_success_url(self):
        """
        Return to previous page. Highlight the updated form and display a success msg.
        """
        return reverse("tf5_list") + f"?highlight={self.anmeldelse_id}"

    def form_valid(self, form, formset):
        self.anmeldelse_id = self.item.id
        self.rest_client.privat_afgiftsanmeldelse.update(
            self.anmeldelse_id,
            form.cleaned_data,
            form.cleaned_data.get("leverandørfaktura"),
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
            self.rest_client.varelinje.create(
                item, privatafgiftsanmeldelse_id=self.anmeldelse_id
            )
        for id, item in data_map.items():
            if id in existing_map.keys():
                self.rest_client.varelinje.update(
                    id,
                    item,
                    existing_map[id],
                    privatafgiftsanmeldelse_id=self.anmeldelse_id,
                )
        for id, item in existing_map.items():
            if id not in data_map:
                self.rest_client.varelinje.delete(id)

        messages.add_message(
            self.request,
            messages.INFO,
            _("Afgiftsanmeldelsen med nummer {id} blev opdateret").format(
                id=self.anmeldelse_id
            ),
        )
        return super().form_valid(form, formset)

    @cached_property
    def toplevel_varesatser(self):
        dato = date.today()
        if self.item.indleveringsdato:
            dato = self.item.indleveringsdato
        if self.request.POST:
            if "indleveringsdato" in self.request.POST:
                dato = date.fromisoformat(self.request.POST["indleveringsdato"])
        return dict(
            filter(
                lambda pair: pair[1].overordnet is None,
                self.rest_client.varesatser_fra(dato, synlig_privat=True).items(),
            )
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["leverandørfaktura_required"] = not self.item.leverandørfaktura
        return kwargs

    def get_formset_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_formset_kwargs()
        # The form_kwargs dict is passed as kwargs to subforms in the formset
        if "form_kwargs" not in kwargs:
            kwargs["form_kwargs"] = {}
        # Will be picked up by TF10VareForm's constructor
        kwargs["form_kwargs"]["varesatser"] = self.toplevel_varesatser
        initial = []
        for item in self.item.varelinjer or []:
            itemdict = dataclasses.asdict(item)
            # Dropdown skal bruge id'er, ikke objekter
            itemdict["vareafgiftssats"] = itemdict["vareafgiftssats"]["id"]
            initial.append(itemdict)
        kwargs["initial"] = initial
        return kwargs

    def get_context_data(self, **context: Dict[str, Any]) -> Dict[str, Any]:
        return super().get_context_data(
            **{
                **context,
                **tf5_common_context(),
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
                "item": self.item,
                "extend_template": self.extend_template,
                "indførselstilladelse": self.item.indførselstilladelse,
            }
        )

    @cached_property
    def item(self) -> PrivatAfgiftsanmeldelse:
        return self.rest_client.privat_afgiftsanmeldelse.get(
            self.kwargs["id"],
            include_varelinjer=True,
            include_notater=False,
        )

    def get_initial(self):
        initial = {}
        item = self.item
        for field in dataclasses.fields(item):
            if field.name != "leverandørfaktura":
                value = getattr(item, field.name)
                if field.name == "cpr":
                    value = str(value).zfill(10)
                initial[field.name] = value
        return initial
