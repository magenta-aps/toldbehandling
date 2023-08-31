from told_common.form_mixins import BootstrapForm
from told_common.rest_client import RestClient
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from requests import HTTPError


class LoginForm(BootstrapForm):
    username = forms.CharField(
        max_length=150,
        min_length=1,
        widget=forms.TextInput(attrs={"placeholder": _("Brugernavn")}),
        required=True,
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": _("Adgangskode")}),
        max_length=150,
        min_length=1,
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = None

    def clean(self):
        if "username" not in self.cleaned_data or "password" not in self.cleaned_data:
            raise ValidationError(_("Login fejlede"))
        try:
            self.token = RestClient.login(
                self.cleaned_data["username"], self.cleaned_data["password"]
            )
        except HTTPError:
            raise ValidationError(_("Login fejlede"))


class TF10GodkendForm(BootstrapForm):
    godkendt = forms.BooleanField(required=False)
