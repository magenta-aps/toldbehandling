# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
import dataclasses
from datetime import date
from functools import cached_property
from typing import Any, Dict

from django.conf import settings
from django.contrib import messages
from django.template import loader
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from told_common import forms as common_forms
from told_common import views as common_views
from told_common.data import PrivatAfgiftsanmeldelse
from told_common.util import dataclass_map_to_dict, opt_str

from ui import forms

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
    form_class = forms.TF5Form
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


class TF5ListView(PermissionsRequiredMixin, HasRestClientMixin, common_views.ListView):
    required_permissions = (
        "anmeldelse.view_afgiftsanmeldelse",
        "anmeldelse.view_varelinje",
    )
    select_template = "told_common/tf5/select.html"
    template_name = "told_common/tf5/list.html"
    extend_template = "told_common/layout.html"
    actions_template = "ui/tf5/actions.html"
    form_class = common_forms.TF5SearchForm
    list_size = 20

    def get_items(self, search_data: Dict[str, Any]):
        # return self.rest_client.get("afgiftsanmeldelse/full", search_data)
        count, items = self.rest_client.privat_afgiftsanmeldelse.list(**search_data)
        return {"count": count, "items": items}

    def get_context_data(self, **context: Dict[str, Any]) -> Dict[str, Any]:
        return super().get_context_data(
            **{
                **context,
                "title": _("Mine indførselstilladelser"),
                "highlight": self.request.GET.get("highlight"),
                "extend_template": self.extend_template,
                "can_create": True,
                "can_cancel": True,
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
        return value

    def get_form_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_form_kwargs()

        kwargs["data"] = self.request.GET.copy()

        # Will be picked up by TF10SearchForm's constructor
        kwargs["varesatser"] = dict(
            filter(
                lambda pair: pair[1].overordnet is None,
                self.rest_client.varesatser_privat.items(),
            )
        )
        kwargs["initial"] = {}
        return kwargs


class TF5View(common_views.CustomLayoutMixin, common_views.TF5View):
    extend_template = "ui/layout.html"


class TF5FormUpdateView(
    PermissionsRequiredMixin, HasRestClientMixin, FormWithFormsetView
):
    required_permissions = (
        "anmeldelse.view_afgiftsanmeldelse",
        "anmeldelse.view_varelinje",
        "anmeldelse.change_afgiftsanmeldelse",
        "anmeldelse.change_varelinje",
    )
    form_class = forms.TF5Form
    formset_class = common_forms.TF10VareFormSet
    template_name = "told_common/tf5/form.html"
    extend_template = "ui/layout.html"

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
            self.request.FILES.get("leverandørfaktura"),
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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["leverandørfaktura_required"] = False
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
                # TODO: Dato for varesatser?
                self.rest_client.varesatser_privat.items(),
            )
        )
        initial = []
        for item in self.item.varelinjer:
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
                "varesatser": dataclass_map_to_dict(
                    self.rest_client.varesatser_fra(self.item.indleveringsdato)
                ),
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
                initial[field.name] = getattr(item, field.name)
        return initial


class TF5LeverandørFakturaView(common_views.LeverandørFakturaView):
    required_permissions = ("anmeldelse.view_privatafgiftsanmeldelse",)
    api = "privat_afgiftsanmeldelse"
    key = "leverandørfaktura"
