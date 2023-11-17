# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
from functools import cached_property
from typing import Any, Dict

from django.urls import reverse
from told_common import forms as common_forms
from told_common import views as common_views

from told_common.view_mixins import (  # isort: skip
    FormWithFormsetView,
    HasRestClientMixin,
    PermissionsRequiredMixin,
)


class TF10FormCreateView(
    PermissionsRequiredMixin, HasRestClientMixin, FormWithFormsetView
):
    form_class = common_forms.TF10Form
    formset_class = common_forms.TF10VareFormSet
    template_name = "told_common/tf10/form.html"
    extend_template = "ui/layout.html"
    required_permissions = (
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
            + "&msg=created"
        )

    def form_valid(self, form, formset):
        if form.cleaned_data["afsender_change_existing"]:
            afsender_id = self.rest_client.afsender.update(
                form.cleaned_data["afsender_existing_id"], form.cleaned_data
            )
        else:
            afsender_id = self.rest_client.afsender.get_or_create(form.cleaned_data)
        if form.cleaned_data["modtager_change_existing"]:
            modtager_id = self.rest_client.modtager.update(
                form.cleaned_data["modtager_existing_id"], form.cleaned_data
            )
        else:
            modtager_id = self.rest_client.modtager.get_or_create(form.cleaned_data)
        postforsendelse_id = self.rest_client.postforsendelse.create(form.cleaned_data)
        fragtforsendelse_id = self.rest_client.fragtforsendelse.create(
            form.cleaned_data, self.request.FILES.get("fragtbrev", None)
        )
        self.anmeldelse_id = self.rest_client.afgiftanmeldelse.create(
            form.cleaned_data,
            self.request.FILES["leverandørfaktura"],
            afsender_id,
            modtager_id,
            postforsendelse_id,
            fragtforsendelse_id,
        )
        for subform in formset:
            if subform.cleaned_data:
                self.rest_client.varelinje.create(
                    subform.cleaned_data, self.anmeldelse_id
                )
        return super().form_valid(form, formset)

    @cached_property
    def toplevel_varesatser(self):
        return dict(
            filter(
                lambda pair: pair[1].get("overordnet", None) is None,
                self.rest_client.varesatser.items(),
            )
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "varesatser": self.toplevel_varesatser,
                "initial": {
                    "afsender_change_existing": False,
                    "modtager_change_existing": False,
                },
            }
        )
        return kwargs

    def get_formset_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_formset_kwargs()
        # The form_kwargs dict is passed as kwargs to subforms in the formset
        if "form_kwargs" not in kwargs:
            kwargs["form_kwargs"] = {}
        # Will be picked up by TF10VareForm's constructor
        kwargs["form_kwargs"]["varesatser"] = dict(
            filter(
                lambda pair: pair[1].get("overordnet", None) is None,
                self.rest_client.varesatser.items(),
            )
        )
        return kwargs

    def get_context_data(self, **context: Dict[str, Any]) -> Dict[str, Any]:
        context = super().get_context_data(
            **{
                **context,
                "varesatser": self.rest_client.varesatser,
                "extend_template": self.extend_template,
            }
        )
        form = context["form"]
        if hasattr(form, "cleaned_data"):
            context.update(
                {
                    "afsender_existing_id": form.cleaned_data.get(
                        "afsender_existing_id", None
                    ),
                    "modtager_existing_id": form.cleaned_data.get(
                        "modtager_existing_id", None
                    ),
                }
            )
        return context


class TF10ListView(common_views.TF10ListView):
    actions_template = "ui/tf10/actions.html"
    extend_template = "ui/layout.html"

    def get_context_data(self, **context):
        return super().get_context_data(**{**context, "can_create": True})


class TF10FormUpdateView(common_views.TF10FormUpdateView):
    extend_template = "ui/layout.html"
