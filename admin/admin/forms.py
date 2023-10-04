# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from datetime import date, timedelta

from admin.data import Vareafgiftssats
from admin.exceptions import SpreadsheetImportException
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from told_common.form_mixins import BootstrapForm, DateInput, MaxSizeFileField


class TF10GodkendForm(BootstrapForm):
    godkendt = forms.BooleanField(required=False)


class ListForm(forms.Form):
    json = forms.BooleanField(required=False)
    offset = forms.IntegerField(required=False)
    limit = forms.IntegerField(required=False)
    sort = forms.CharField(required=False)
    order = forms.CharField(required=False)


class AfgiftstabelSearchForm(ListForm):
    pass


class AfgiftstabelUpdateForm(BootstrapForm):
    kladde = forms.ChoiceField(
        required=False, choices=((True, _("Ja")), (False, _("Nej")))
    )
    gyldig_fra = forms.DateField(
        required=False,
        widget=DateInput(attrs={"min": (date.today() + timedelta(1)).isoformat()}),
    )
    delete = forms.BooleanField(required=False)

    def clean(self, *args, **kwargs):
        data = self.cleaned_data
        if not data.get("delete", None):
            for required_field in ("kladde", "gyldig_fra"):
                if not data.get(required_field, None):
                    self.add_error(
                        required_field,
                        ValidationError(
                            self.fields[required_field].error_messages["required"],
                            "required",
                        ),
                    )
        return data

    def clean_gyldig_fra(self):
        value = self.cleaned_data.get("gyldig_fra", None)
        if value is not None and value <= date.today():
            raise ValidationError(_("Dato skal være efter i dag"))
        return value


class AfgiftstabelCreateForm(BootstrapForm):
    fil = MaxSizeFileField(
        required=True,
        max_size=10000000,
    )

    def __init__(self, *args, **kwargs):
        self.parsed_satser = None
        super().__init__(*args, **kwargs)

    def clean_fil(self):
        data = self.cleaned_data["fil"]
        try:
            if data.content_type == "text/csv":
                satser = Vareafgiftssats.load_csv(data)
            elif (
                data.content_type
                == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ):
                satser = Vareafgiftssats.load_xlsx(data)
            else:
                raise ValidationError(f"Ugyldig content-type: {data.content_type}")
            Vareafgiftssats.validate_satser(satser)
        except SpreadsheetImportException as e:
            raise ValidationError(e)
        self.parsed_satser = satser
        return data
