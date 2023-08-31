from typing import Dict, Any

from django.urls import reverse
from told_common.view_mixins import (
    FormWithFormsetView,
    LoginRequiredMixin,
    HasRestClientMixin,
)

from ui import forms


class TF10FormView(LoginRequiredMixin, HasRestClientMixin, FormWithFormsetView):
    form_class = forms.TF10Form
    formset_class = forms.TF10VareFormSet
    template_name = "ui/tf10/form.html"

    def get_success_url(self):
        return reverse("tf10_blanket_success")

    def form_valid(self, form, formset):
        afsender_id = self.rest_client.get_or_create_afsender(form.cleaned_data)
        modtager_id = self.rest_client.get_or_create_modtager(form.cleaned_data)
        postforsendelse_id = self.rest_client.create_postforsendelse(form.cleaned_data)
        fragtforsendelse_id = self.rest_client.create_fragtforsendelse(
            form.cleaned_data, self.request.FILES.get("fragtbrev", None)
        )
        anmeldelse_id = self.rest_client.create_anmeldelse(
            self.request,
            form.cleaned_data,
            afsender_id,
            modtager_id,
            postforsendelse_id,
            fragtforsendelse_id,
        )
        self.rest_client.create_varelinjer(
            [subform.cleaned_data for subform in formset], anmeldelse_id
        )
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
            **{**context, "varesatser": self.rest_client.varesatser}
        )
