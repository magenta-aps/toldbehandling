# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from datetime import date, timedelta
from typing import List

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from told_common import forms as common_forms
from told_common.form_mixins import BootstrapForm, DateInput, MaxSizeFileField

from admin.spreadsheet import (  # isort: skip
    SpreadsheetImportException,
    VareafgiftssatsSpreadsheetUtil,
)


class TF10CreateForm(common_forms.TF10Form):
    oprettet_på_vegne_af = forms.ChoiceField(label=_("Opret på vegne af"))

    def __init__(self, oprettet_på_vegne_af_choices: List[dict], **kwargs):
        super().__init__(**kwargs)
        self.fields["oprettet_på_vegne_af"].choices = oprettet_på_vegne_af_choices


class TF10ViewForm(BootstrapForm):
    godkendt = forms.BooleanField(required=False)
    # For at vi kan have tre formfelter i hver sin modal
    notat1 = forms.CharField(
        widget=forms.Textarea(attrs={"placeholder": _("Notat")}), required=False
    )
    notat2 = forms.CharField(
        widget=forms.Textarea(attrs={"placeholder": _("Notat")}), required=False
    )
    notat3 = forms.CharField(
        widget=forms.Textarea(attrs={"placeholder": _("Notat")}), required=False
    )
    send_til_prisme = forms.BooleanField(required=False)


class TF10UpdateForm(common_forms.TF10Form):
    notat = forms.CharField(
        widget=forms.Textarea(attrs={"placeholder": _("Notat")}), required=False
    )


class TF10UpdateMultipleForm(BootstrapForm):
    forbindelsesnr = forms.CharField(
        required=False,
    )
    fragtbrevnr = forms.CharField(
        required=False,
    )
    afgangsdato = forms.DateField(
        required=False,
        widget=DateInput,
        label=_("Afgangsdato"),
    )
    notat = forms.CharField(
        widget=forms.Textarea(attrs={"placeholder": _("Notat")}), required=False
    )

    def __init__(self, fragttype, **kwargs):
        super().__init__(**kwargs)
        if fragttype in ("skibsfragt", "luftfragt"):
            self.fields["forbindelsesnr"].label = _("Forbindelsesnummer")
            self.fields["fragtbrevnr"].label = _("Fragtbrevnr")
        elif fragttype in ("skibspost", "luftpost"):
            self.fields["forbindelsesnr"].label = _("Afsenderbykode")
            self.fields["forbindelsesnr"].disabled = True
            self.fields["fragtbrevnr"].label = _("Postforsendelsesnummer")
        else:
            self.fields["forbindelsesnr"].disabled = True
            self.fields["fragtbrevnr"].disabled = True
            self.fields["afgangsdato"].disabled = True


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
        if not data.get("delete"):
            for required_field in ("kladde", "gyldig_fra"):
                if not data.get(required_field):
                    self.add_error(
                        required_field,
                        ValidationError(
                            self.fields[required_field].error_messages["required"],
                            "required",
                        ),
                    )
        return data

    def clean_gyldig_fra(self):
        value = self.cleaned_data.get("gyldig_fra")
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
                satser = VareafgiftssatsSpreadsheetUtil.load_csv(data)
            elif (
                data.content_type
                == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ):
                satser = VareafgiftssatsSpreadsheetUtil.load_xlsx(data)
            else:
                raise ValidationError(f"Ugyldig content-type: {data.content_type}")
            VareafgiftssatsSpreadsheetUtil.validate_satser(satser)
        except SpreadsheetImportException as e:
            raise ValidationError(e)
        self.parsed_satser = satser
        return data


class TF10PrismeSendForm(forms.Form):
    afgiftsanmeldelse = forms.IntegerField(widget=forms.HiddenInput())
