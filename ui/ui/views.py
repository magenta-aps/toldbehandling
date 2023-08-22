from typing import Dict, Any

from django.http import JsonResponse
from django.urls import reverse
from django.views import View
from django.views.generic import FormView, RedirectView
from ui.view_mixins import FormWithFormsetView, LoginRequiredMixin, HasRestClientMixin

from ui import forms


class LoginView(FormView):
    form_class = forms.LoginForm
    template_name = "ui/login.html"

    def get_success_url(self):
        next = self.request.GET.get("next", None)
        if next:
            return next
        return reverse("tf10_blanket")

    def form_valid(self, form):
        response = super().form_valid(form)
        form.token.synchronize(response, synchronize_refresh_token=True)
        return response


class LogoutView(RedirectView):
    pattern_name = "login"

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        return response


class RestView(LoginRequiredMixin, HasRestClientMixin, View):
    def get(self, request, *args, **kwargs) -> JsonResponse:
        data = self.rest_client.get(kwargs["path"], request.GET)
        return JsonResponse(data)


class TF10FormView(LoginRequiredMixin, HasRestClientMixin, FormWithFormsetView):
    form_class = forms.TF10Form
    formset_class = forms.TF10VareFormSet
    template_name = "ui/tf10/blanket.html"

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
