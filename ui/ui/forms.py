# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
from datetime import date
from typing import Optional

from django import forms
from django.core.validators import RegexValidator
from django.forms import CharField
from django.utils.translation import gettext_lazy as _
from told_common.util import date_next_workdays

from told_common.form_mixins import (  # isort: skip
    BootstrapForm,
    ButtonlessIntegerField,
    DateInput,
    MaxSizeFileField,
)


class TF5Form(BootstrapForm):
    def __init__(
        self,
        varesatser: Optional[dict] = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.varesatser = varesatser
        self.fields["indleveringsdato"].widget.attrs.update(
            {"min": date_next_workdays(date.today(), 6)}
        )
        if "initial" in kwargs:
            for field in ("cpr", "navn"):
                if field in kwargs["initial"]:
                    self.fields[field].widget.attrs["readonly"] = "readonly"

    cpr = CharField(
        label=_("CPR"),
        required=True,
        error_messages={
            "invalid": _("CPR-nummer skal være på 10 cifre"),
        },
        validators=(RegexValidator(r"\d{10}"),),
    )
    navn = forms.CharField(
        max_length=100,
        label=_("Navn"),
        required=True,
    )
    adresse = forms.CharField(
        max_length=100,
        required=True,
        label=_("Vej og husnummer"),
    )
    postnummer = ButtonlessIntegerField(
        min_value=1000,
        max_value=9999,
        required=True,
        label=_("Postnr."),
        error_messages={
            "invalid": _("Postnummer skal være på 4 cifre og må ikke begynde med 0"),
            "min_value": _("Postnummer skal være på 4 cifre og må ikke begynde med 0"),
            "max_value": _("Postnummer skal være på 4 cifre og må ikke begynde med 0"),
        },
    )
    by = forms.CharField(
        max_length=20,
        required=True,
        label=_("By"),
    )
    telefon = forms.CharField(
        max_length=12,
        required=True,
        label=_("Telefon"),
    )
    bookingnummer = forms.CharField(
        max_length=128,
        required=True,
        label=_("Bookingnummer"),
    )
    leverandørfaktura_nummer = forms.CharField(
        label=_("Varefakturanummer"),
        max_length=20,
        required=True,
    )
    leverandørfaktura = MaxSizeFileField(
        allow_empty_file=False,
        label=_("Vare­faktura"),
        max_size=10000000,
        required=True,
        widget=forms.widgets.ClearableFileInput(
            attrs={
                "data-tooltip-title": _("Varefaktura"),
                "data-tooltip-content": _("Vedhæftning af varefaktura"),
            }
        ),
    )
    indleveringsdato = forms.DateField(
        label=_("Dato for indlevering til forsendelse"),
        required=True,
        widget=DateInput(),
    )
    anonym = forms.BooleanField(
        required=False,
    )
