# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
from django import forms


class TF5TilladelseForm(forms.Form):
    opret = forms.BooleanField(required=False)
    send = forms.BooleanField(required=False)
