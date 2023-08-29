from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from requests import HTTPError
from admin.rest_client import RestClient


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150, widget=forms.TextInput(attrs={"placeholder": _("Brugernavn")})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": _("Adgangskode")})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = None

    def clean(self):
        try:
            self.token = RestClient.login(
                self.cleaned_data["username"], self.cleaned_data["password"]
            )
        except HTTPError:
            raise ValidationError(_("Login fejlede"))


class TF10GodkendForm(forms.Form):
    godkend = forms.CharField(required=True)
