# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

from datetime import datetime, timezone
from typing import List

import django.utils.timezone as tz
from dateutil.tz import tzoffset
from django import forms
from django.core.exceptions import ValidationError
from django.forms import Select, formset_factory
from django.utils.translation import gettext_lazy as _
from dynamic_forms import DynamicField
from tempus_dominus.widgets import DateTimePicker
from told_common import forms as common_forms
from told_common.form_mixins import (
    BootstrapForm,
    DateInput,
    FixedWidthIntegerField,
    MaxSizeFileField,
    ModifiableCheckboxSelectMultiple,
    MultipleSeparatedChoiceField,
)

from admin.spreadsheet import SpreadsheetImportException, VareafgiftssatsSpreadsheetUtil


class TF10CreateForm(common_forms.TF10Form):
    oprettet_på_vegne_af = DynamicField(
        forms.ChoiceField,
        label=_("Opret på vegne af"),
        widget=Select(attrs={"autocomplete": "off", "required-on-draft": "true"}),
        choices=lambda form: [(None, "---")] + list(form.oprettet_på_vegne_af_choices),
    )
    tf3 = forms.BooleanField(
        required=False,
        label=_("Indførsel fra tredjeland"),
        widget=forms.Select(choices=[(False, _("Nej")), (True, _("Ja"))]),
    )

    def __init__(self, oprettet_på_vegne_af_choices: List[dict], **kwargs):
        self.oprettet_på_vegne_af_choices = oprettet_på_vegne_af_choices
        super().__init__(**kwargs)


class TF10ViewForm(BootstrapForm):
    def __init__(self, toldkategorier, *args, **kwargs):
        self.toldkategorier = toldkategorier
        super().__init__(*args, **kwargs)

    status = forms.ChoiceField(
        required=False,
        choices=(
            ("ny", _("Ny")),
            ("godkendt", _("Godkendt")),
            ("afvist", _("Afvist")),
        ),
    )
    # For at vi kan have tre formfelter i hver sin modal
    notat1 = forms.CharField(
        widget=forms.Textarea(
            attrs={"placeholder": _("Notat"), "disabled": "disabled"}
        ),
        required=False,
    )
    notat2 = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "placeholder": _("Notat"),
                "disabled": "disabled",
                "data-modal-required": "true",
            }
        ),
        required=False,
    )
    notat3 = forms.CharField(
        widget=forms.Textarea(
            attrs={"placeholder": _("Notat"), "disabled": "disabled"}
        ),
        required=False,
    )
    send_til_prisme = forms.BooleanField(required=False)
    toldkategori = DynamicField(
        forms.ChoiceField,
        required=False,
        choices=lambda form: [
            (item.kategori, f"{item.kategori} - {item.navn}")
            for item in form.toldkategorier
        ],
        widget=forms.Select(
            attrs={"disabled": "disabled", "data-modal-required": "true"}
        ),
    )
    modtager_stedkode = FixedWidthIntegerField(
        required=False,
        label=_("Stedkode"),
        width=3,
        widget=forms.TextInput(
            attrs={"disabled": "disabled", "data-modal-required": "true"}
        ),
    )

    def clean(self):
        if self.cleaned_data.get("send_til_prisme"):
            if (
                "toldkategori" not in self.cleaned_data
                or self.cleaned_data["toldkategori"] == ""
            ):
                self.add_error(
                    "toldkategori",
                    ValidationError(
                        "Der skal vælges en toldkategori når der sendes til Prisme"
                    ),
                )
            if not self.cleaned_data.get("modtager_stedkode"):
                self.add_error(
                    "modtager_stedkode",
                    ValidationError(
                        "Der skal vælges en stedkode når der sendes til Prisme"
                    ),
                )


class TF10UpdateForm(common_forms.TF10Form):
    def __init__(self, toldkategorier, *args, **kwargs):
        self.toldkategorier = toldkategorier
        super().__init__(*args, **kwargs)

    toldkategori = DynamicField(
        forms.ChoiceField,
        required=False,
        choices=lambda form: [(None, "---------")]
        + [
            (item.kategori, f"{item.kategori} - {item.navn}")
            for item in form.toldkategorier
        ],
    )
    tf3 = forms.BooleanField(
        required=False,
        label=_("Indførsel fra tredjeland"),
        widget=forms.Select(choices=[(False, _("Nej")), (True, _("Ja"))]),
    )


class TF10UpdateMultipleForm(BootstrapForm):
    forbindelsesnr = DynamicField(
        forms.CharField,
        required=False,
        label=lambda form: (
            _("Forbindelsesnummer")
            if form.fragttype in ("skibsfragt", "luftfragt")
            else _("Afsenderbykode")
        ),
        disabled=lambda form: form.fragttype not in ("skibsfragt", "luftfragt"),
    )
    fragtbrevnr = DynamicField(
        forms.CharField,
        required=False,
        label=lambda form: (
            _("Fragtbrevnr")
            if form.fragttype in ("skibsfragt", "luftfragt")
            else _("Postforsendelsesnummer")
        ),
        disabled=lambda form: form.fragttype
        not in ("skibsfragt", "luftfragt", "skibspost", "luftpost"),
    )
    afgangsdato = DynamicField(
        forms.DateField,
        required=False,
        widget=DateInput(),
        label=_("Afgangsdato"),
        disabled=lambda form: form.fragttype
        not in ("skibsfragt", "luftfragt", "skibspost", "luftpost"),
    )
    notat = forms.CharField(
        widget=forms.Textarea(attrs={"placeholder": _("Notat")}), required=False
    )

    def __init__(self, fragttype, **kwargs):
        self.fragttype = fragttype
        super().__init__(**kwargs)


class TF10SearchForm(common_forms.TF10SearchForm):
    def __init__(self, toldkategorier, *args, **kwargs):
        self.toldkategorier = toldkategorier
        super().__init__(*args, **kwargs)

    status_choices_all = common_forms.TF10SearchForm.status_choices_all + [
        ("slettet", _("Slettet")),
    ]

    toldkategori = DynamicField(
        forms.MultipleChoiceField,
        choices=lambda form: [("no_category", _("Ingen kategori"))]
        + [
            (toldkategori.kategori, f"{toldkategori.kategori} - {toldkategori.navn}")
            for toldkategori in form.toldkategorier
        ],
        required=False,
        widget=ModifiableCheckboxSelectMultiple(attrs={}, subwidget_attrs={"class": "form-check-input"})
    )


class ListForm(forms.Form):
    json = forms.BooleanField(required=False)
    offset = forms.IntegerField(required=False)
    limit = forms.IntegerField(required=False)
    sort = forms.CharField(required=False)
    order = forms.CharField(required=False)


class AfgiftstabelSearchForm(ListForm):
    pass


class AfgiftstabelUpdateForm(BootstrapForm):
    format = "%Y-%m-%dT%H:%M:%S%z"

    kladde = forms.ChoiceField(
        required=False, choices=((True, _("Ja")), (False, _("Nej")))
    )
    gyldig_fra = DynamicField(
        forms.DateTimeField,  # Vil konvertere naive datetime-input fra klienten
        # til aware datetimes ud fra settings.TIME_ZONE
        input_formats=["%d/%m/%Y %H:%M"],
        required=False,
        widget=lambda form: DateTimePicker(
            format=form.format,
            options={
                "minDate": datetime.now().isoformat(),
                "sideBySide": True,
            },
        ),
    )
    offset = forms.IntegerField(required=False, widget=forms.HiddenInput)
    delete = forms.BooleanField(required=False)

    def clean(self, *args, **kwargs):
        data = self.cleaned_data
        if not data.get("delete"):
            for required_field in ("gyldig_fra",):
                if not data.get(required_field):
                    self.add_error(
                        required_field,
                        ValidationError(
                            self.fields[required_field].error_messages["required"],
                            "required",
                        ),
                    )
        gyldig_fra = data.get("gyldig_fra")
        if gyldig_fra:
            # Django modtager en naiv datetime fra klienten,
            # som den sætter settings.TIME_ZONE på
            # Vi skal erstatte den tidszone med det offset vi
            # får i et separat felt, så det kommer til at passe
            offset = data.get("offset")
            if offset in (None, ""):
                gyldig_fra = datetime.combine(
                    gyldig_fra.date(),
                    gyldig_fra.time(),
                    tz.get_default_timezone(),
                )
            else:
                gyldig_fra = datetime.combine(
                    gyldig_fra.date(),
                    gyldig_fra.time(),
                    tzoffset("offset", offset * 60),
                )
            data["gyldig_fra"] = gyldig_fra
        return data

    def clean_gyldig_fra(self):
        value = self.cleaned_data.get("gyldig_fra")
        if value is not None and value <= datetime.now(timezone.utc):
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


class StatistikForm(BootstrapForm):
    anmeldelsestype = forms.ChoiceField(
        choices=(
            (None, "Alle"),
            ("tf5", "Private afgiftsanmeldelser (TF5)"),
            ("tf10", "Afgiftsanmeldelser (TF10)"),
        ),
        required=False,
    )
    startdato = forms.DateField(required=False, widget=DateInput())
    slutdato = forms.DateField(required=False, widget=DateInput())
    download = forms.BooleanField(required=False)


class StatistikGruppeForm(BootstrapForm):
    def __init__(self, gruppe_choices, *args, **kwargs):
        self.gruppe_choices = gruppe_choices
        super().__init__(*args, **kwargs)

    gruppe = DynamicField(
        MultipleSeparatedChoiceField,
        choices=lambda form: ((str(gruppe), gruppe) for gruppe in form.gruppe_choices),
        delimiters=["+", ","],
    )


StatistikGruppeFormSet = formset_factory(
    StatistikGruppeForm, min_num=0, extra=1, can_delete=True
)


class TF5Form(common_forms.TF5Form):
    notat = forms.CharField(
        widget=forms.Textarea(attrs={"placeholder": _("Notat")}), required=False
    )
    indleveringsdato_ubegrænset = True


class TF5ViewForm(common_forms.TF5ViewForm):
    betalt = forms.BooleanField(required=False)


class TF5SearchForm(common_forms.TF5SearchForm):
    notat = forms.CharField(required=False)
