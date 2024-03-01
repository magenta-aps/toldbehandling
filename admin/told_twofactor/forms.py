from django.conf import settings
from two_factor import forms as twofactor_forms
from told_common import forms as common_forms
from told_common.form_mixins import BootstrapForm
from django.utils.translation import gettext_lazy as _
from django import forms
from told_common.form_mixins import (
    FixedWidthIntegerField,
)

class AuthenticationTokenForm(twofactor_forms.AuthenticationTokenForm, BootstrapForm):
    def __init__(self, user, initial_device, **kwargs):
        """
        Overwritten to set a Danish label on the `remember` field.
        """
        super().__init__(user, initial_device, **kwargs)
        self.fields["remember"] = forms.BooleanField(
            required=False,
            initial=True,
            label=_("Husk mig på denne maskine i {days} dage").format(
                days=int(settings.TWO_FACTOR_REMEMBER_COOKIE_AGE / 3600 / 24)
            ),
        )


class TwofactorLoginForm(common_forms.LoginForm):

    twofactor = FixedWidthIntegerField(
        widget_attrs={"placeholder": _("Tofaktor-token")},
        width=6,
    )
