from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from requests import HTTPError
from told_common.form_mixins import BootstrapForm, FixedWidthIntegerField
from told_common.rest_client import RestClient
from two_factor import forms as twofactor_forms


class AuthenticationTokenForm(twofactor_forms.AuthenticationTokenForm, BootstrapForm):
    pass


class TwofactorLoginForm(BootstrapForm):
    def __init__(self, *args, **kwargs):
        self.user_id = kwargs.pop("user_id")
        super().__init__(*args, **kwargs)

    twofactor_token = FixedWidthIntegerField(
        widget_attrs={
            "label": _("Tofaktor-token"),
            "autofocus": "true",
            "data-validity-patternmismatch": _("Token skal være et tal på seks cifre")
        },
        width=6,
    )

    def clean_twofactor_token(self):
        try:
            self.token = RestClient.check_twofactor(
                self.user_id, self.cleaned_data["twofactor_token"]
            )
        except HTTPError:
            raise ValidationError(_("Ugyldig token"))
        return self.cleaned_data["twofactor_token"]


class TOTPDeviceForm(twofactor_forms.TOTPDeviceForm, BootstrapForm):

    error_messages = {'invalid_token': _("Ugyldig token")}

    def __init__(self, key, user, metadata=None, **kwargs):
        self.view = kwargs.pop("view", None)
        super().__init__(key, user, metadata, **kwargs)

    def save(self):
        self.view.rest_client.totpdevice.create(
            {
                "user_id": self.user.id,
                "key": self.key,
                "tolerance": self.tolerance,
                "t0": self.t0,
                "step": self.step,
                "drift": self.drift,
                "digits": self.digits,
                "name": "default",
            }
        )
