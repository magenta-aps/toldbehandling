import os
from typing import Union, Dict, Any
from urllib.parse import unquote

from django.conf import settings
from django.http import JsonResponse, FileResponse, Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import FormView, RedirectView
from requests import HTTPError
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


class TF10View(LoginRequiredMixin, HasRestClientMixin, FormView):
    template_name = "ui/tf10/view.html"
    form_class = forms.TF10GodkendForm

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **{
                **kwargs,
                "object": self.get_object(),
            }
        )

    def form_valid(self, form):
        if form.cleaned_data["godkend"] == "1":
            anmeldelse_id = self.kwargs["id"]
            try:
                self.rest_client.patch(
                    f"afgiftsanmeldelse/{anmeldelse_id}", {"godkendt": True}
                )
                return redirect(reverse("tf10_view", kwargs={"id": anmeldelse_id}))
            except HTTPError as e:
                if e.response.status_code == 404:
                    raise Http404("Afgiftsanmeldelse findes ikke")
                raise
        else:
            return self.form_invalid(form)

    def get_object(self):
        try:
            anmeldelse = self.get_data("afgiftsanmeldelse", self.kwargs["id"])
        except HTTPError as e:
            if e.response.status_code == 404:
                raise Http404("Afgiftsanmeldelse findes ikke")
            raise
        for key in ("afsender", "modtager", "fragtforsendelse", "postforsendelse"):
            if anmeldelse[key] is not None:
                anmeldelse[key] = self.get_data(key, anmeldelse[key])
        anmeldelse["varelinjer"] = self.rest_client.get(
            "varelinje", {"afgiftsanmeldelse": anmeldelse["id"]}
        )["items"]
        satser = {}
        for varelinje in anmeldelse["varelinjer"]:
            sats_id = varelinje["afgiftssats"]
            if sats_id not in satser:
                satser[sats_id] = self.get_data("vareafgiftssats", sats_id)
            varelinje["afgiftssats"] = satser[sats_id]
        return anmeldelse

    def get_data(self, api, id) -> Union[dict, None]:
        # Filfelter som indeholder en sti der er urlquotet af Django Ninja
        unquote_keys = (
            ("afgiftsanmeldelse", "leverandørfaktura"),
            ("fragtforsendelse", "fragtbrev"),
        )
        data = self.rest_client.get(f"{api}/{id}")
        for key_api, key_field in unquote_keys:
            if api == key_api and data.get(key_field, None):
                data[key_field] = unquote(data[key_field])
        return data


class FileView(LoginRequiredMixin, HasRestClientMixin, View):
    def get(self, request, *args, **kwargs):
        object = self.rest_client.get(
            f"{self.api}/{kwargs['id']}"
        )  # Vil kaste 404 hvis id ikke findes
        # settings.MEDIA_ROOT er monteret i Docker så det deles mellem
        # containerne REST og UI.
        # Derfor kan vi læse filer der er skrevet af den anden container
        path = os.path.join(settings.MEDIA_ROOT, unquote(object[self.key]).lstrip("/"))
        return FileResponse(open(path, "rb"))


class LeverandørFakturaView(FileView):
    api = "afgiftsanmeldelse"
    key = "leverandørfaktura"


class FragtbrevView(FileView):
    api = "fragtforsendelse"
    key = "fragtbrev"
