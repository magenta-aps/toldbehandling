from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from requests import HTTPError
from told_common import forms as common_forms
from told_common.form_mixins import BootstrapForm, FixedWidthIntegerField
from told_common.rest_client import RestClient
from two_factor import forms as twofactor_forms


class AuthenticationTokenForm(twofactor_forms.AuthenticationTokenForm, BootstrapForm):
    def __init__(self, user, initial_device, **kwargs):
        """
        Overwritten to set a Danish label on the `remember` field.
        """
        super().__init__(user, initial_device, **kwargs)
        # self.fields["remember"] = forms.BooleanField(
        #     required=False,
        #     initial=True,
        #     label=_("Husk mig på denne maskine i {days} dage").format(
        #         days=int(settings.TWO_FACTOR_REMEMBER_COOKIE_AGE / 3600 / 24)
        #     ),
        # )


class TwofactorLoginForm(BootstrapForm):
    def __init__(self, *args, **kwargs):
        self.user_id = kwargs.pop("user_id")
        print(f"self.user_id: {self.user_id}")
        super().__init__(*args, **kwargs)

    twofactor_token = FixedWidthIntegerField(
        widget_attrs={"placeholder": _("Tofaktor-token"), "autofocus": "true"},
        width=6,
    )

    def clean(self):
        try:
            self.token = RestClient.check_twofactor(
                self.user_id, self.cleaned_data["twofactor_token"]
            )
        except HTTPError:
            raise ValidationError(_("Login fejlede"))


class TwofactorLoginForm1(common_forms.LoginForm):
    twofactor_token = FixedWidthIntegerField(
        widget_attrs={"placeholder": _("Tofaktor-token")},
        width=6,
    )

    def clean(self):
        if "username" not in self.cleaned_data or "password" not in self.cleaned_data:
            raise ValidationError(_("Login fejlede"))
        try:
            self.token = RestClient.login_twofactor(
                self.cleaned_data["username"],
                self.cleaned_data["password"],
                self.cleaned_data["twofactor_token"],
            )
        except HTTPError:
            raise ValidationError(_("Login fejlede"))


# TODO: Bedre oversættelser af labels og fejlmeddelselser i forms


class TOTPDeviceForm(twofactor_forms.TOTPDeviceForm, BootstrapForm):
    def __init__(self, key, user, metadata=None, **kwargs):
        self.view = kwargs.pop("view", None)
        super().__init__(key, user, metadata, **kwargs)

    def save(self):
        print("SAVE")
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
