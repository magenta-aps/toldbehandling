# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
from django import forms
from django.utils.translation import gettext_lazy as _
from told_common.form_mixins import BootstrapForm


class TF5TilladelseForm(forms.Form):
    opret = forms.BooleanField(required=False)
    send = forms.BooleanField(required=False)


class TF10ViewForm(BootstrapForm):
    status = forms.ChoiceField(
        required=False,
        choices=(
            ("ny", _("Ny")),
            ("afvist", _("Afvist")),
        ),
    )
