from typing import Dict, Any

from django.urls import reverse
from told_common import forms as common_forms
from told_common import views as common_views
from told_common.view_mixins import (
    FormWithFormsetView,
    LoginRequiredMixin,
    HasRestClientMixin,
)


class TF10FormCreateView(LoginRequiredMixin, HasRestClientMixin, FormWithFormsetView):
    form_class = common_forms.TF10Form
    formset_class = common_forms.TF10VareFormSet
    template_name = "told_common/tf10/form.html"
    extend_template = "ui/layout.html"

    def get_success_url(self):
        return reverse("tf10_blanket_success")

    def form_valid(self, form, formset):
        afsender_id = self.rest_client.afsender.get_or_create(form.cleaned_data)
        modtager_id = self.rest_client.modtager.get_or_create(form.cleaned_data)
        postforsendelse_id = self.rest_client.postforsendelse.create(form.cleaned_data)
        fragtforsendelse_id = self.rest_client.fragtforsendelse.create(
            form.cleaned_data, self.request.FILES.get("fragtbrev", None)
        )
        anmeldelse_id = self.rest_client.afgiftanmeldelse.create(
            form.cleaned_data,
            self.request.FILES["leverandørfaktura"],
            afsender_id,
            modtager_id,
            postforsendelse_id,
            fragtforsendelse_id,
        )
        for subform in formset:
            if subform.cleaned_data:
                self.rest_client.varelinje.create(subform.cleaned_data, anmeldelse_id)
        return super().form_valid(form, formset)

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
        return super().get_context_data(
            **{
                **context,
                "varesatser": self.rest_client.varesatser,
                "extend_template": self.extend_template,
            }
        )


class TF10ListView(common_views.TF10ListView):
    actions_template = "ui/tf10/link.html"
    extend_template = "ui/layout.html"

    def get_context_data(self, **context):
        return super().get_context_data(**{**context, "can_create": True})
