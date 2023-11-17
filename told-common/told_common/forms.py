# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
from datetime import date
from typing import Optional

from django import forms
from django.core.exceptions import ValidationError
from django.forms import Form, formset_factory
from django.utils.translation import gettext_lazy as _
from requests import HTTPError
from told_common.rest_client import RestClient

from told_common.form_mixins import (  # isort: skip
    BootstrapForm,
    ButtonlessIntegerField,
    DateInput,
    MaxSizeFileField,
)


class LoginForm(BootstrapForm):
    username = forms.CharField(
        max_length=150,
        min_length=1,
        widget=forms.TextInput(attrs={"placeholder": _("Brugernavn")}),
        required=True,
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": _("Adgangskode")}),
        max_length=150,
        min_length=1,
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = None

    def clean(self):
        if "username" not in self.cleaned_data or "password" not in self.cleaned_data:
            raise ValidationError(_("Login fejlede"))
        try:
            self.token = RestClient.login(
                self.cleaned_data["username"], self.cleaned_data["password"]
            )
        except HTTPError:
            raise ValidationError(_("Login fejlede"))


class TF10Form(BootstrapForm):
    def __init__(
        self,
        leverandørfaktura_required: bool = True,
        fragtbrev_required: bool = True,
        varesatser: Optional[dict] = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        if not leverandørfaktura_required:
            self.fields["leverandørfaktura"].required = False
        self.leverandørfaktura_required = leverandørfaktura_required
        self.fragtbrev_required = fragtbrev_required
        self.varesatser = varesatser

    afsender_cvr = ButtonlessIntegerField(
        min_value=10000000,
        max_value=99999999,
        label=_("CVR"),
        required=False,
        error_messages={
            "invalid": _("CVR-nummer skal være på 8 cifre og må ikke begynde med 0"),
            "min_value": _("CVR-nummer skal være på 8 cifre og må ikke begynde med 0"),
            "max_value": _("CVR-nummer skal være på 8 cifre og må ikke begynde med 0"),
        },
    )
    afsender_navn = forms.CharField(
        max_length=100,
        label=_("Navn"),
        required=True,
    )
    afsender_adresse = forms.CharField(
        max_length=100,
        required=True,
        label=_("Vej og husnummer"),
    )
    afsender_postnummer = ButtonlessIntegerField(
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
    afsender_by = forms.CharField(
        max_length=20,
        required=True,
        label=_("By"),
    )
    afsender_postbox = forms.CharField(
        max_length=10,
        required=False,
        label=_("Postbox"),
    )
    afsender_telefon = forms.CharField(
        max_length=12,
        required=True,
        label=_("Tlf."),
    )
    afsender_existing_id = forms.IntegerField(required=False, widget=forms.Select)
    afsender_change_existing = forms.BooleanField(
        required=False,
        widget=forms.RadioSelect(
            choices=(
                (False, _("Opret en ny afsender med de indtastede oplysninger")),
                (True, _("Opdatér den valgte afsender med de indtastede oplysinger")),
            )
        ),
    )

    modtager_cvr = ButtonlessIntegerField(
        min_value=10000000,
        max_value=99999999,
        label=_("CVR"),
        required=False,
        error_messages={
            "invalid": _("CVR-nummer skal være på 8 cifre og må ikke begynde med 0"),
            "min_value": _("CVR-nummer skal være på 8 cifre og må ikke begynde med 0"),
            "max_value": _("CVR-nummer skal være på 8 cifre og må ikke begynde med 0"),
        },
    )
    modtager_navn = forms.CharField(
        max_length=100,
        label=_("Navn"),
        required=True,
    )
    modtager_adresse = forms.CharField(
        max_length=100,
        required=True,
        label=_("Vej og husnummer"),
    )
    modtager_postnummer = ButtonlessIntegerField(
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
    modtager_by = forms.CharField(
        max_length=20,
        required=True,
        label=_("By"),
    )

    modtager_postbox = forms.CharField(
        max_length=10,
        required=False,
        label=_("Postbox"),
    )
    modtager_telefon = forms.CharField(
        max_length=12,
        required=True,
        label=_("Tlf."),
    )
    modtager_existing_id = forms.IntegerField(required=False, widget=forms.Select)
    modtager_change_existing = forms.BooleanField(
        required=False,
        widget=forms.RadioSelect(
            choices=(
                (False, _("Opret en ny modtager med de indtastede oplysninger")),
                (True, _("Opdatér den valgte modtager med de indtastede oplysinger")),
            )
        ),
    )
    indførselstilladelse = forms.CharField(
        max_length=12, required=False, label=_("Indførsels­tilladelse nr.")
    )
    leverandørfaktura_nummer = forms.CharField(
        label=_("Leverandør­faktura nr."),
        max_length=20,
    )
    leverandørfaktura = MaxSizeFileField(
        allow_empty_file=False,
        label=_("Leverandør­faktura"),
        max_size=10000000,
    )
    fragtbrev = MaxSizeFileField(
        allow_empty_file=False,
        label=_("Fragtbrev"),
        max_size=10000000,
        required=False,
    )
    fragttype = forms.ChoiceField(
        required=True,
        choices=(
            ("skibsfragt", _("Skibsfragt")),
            ("luftfragt", _("Luftfragt")),
            ("skibspost", _("Skibspost")),
            ("luftpost", _("Luftpost")),
        ),
    )
    forbindelsesnr = forms.CharField(
        required=True,
    )
    fragtbrevnr = forms.CharField(
        required=True,
    )
    betales_af = forms.ChoiceField(
        required=False,
        choices=(
            ("Modtager", _("Modtager")),
            ("Afsender", _("Afsender")),
        ),
    )
    afgangsdato = forms.DateField(
        required=True,
        widget=DateInput(attrs={"min": date.today().isoformat()}),
    )

    def clean(self):
        if (
            self.fragtbrev_required
            and self.cleaned_data["fragttype"]
            in (
                "skibsfragt",
                "luftfragt",
            )
            and not self.files.get("fragtbrev")
        ):
            raise ValidationError(
                {
                    "fragtbrev": _("Mangler fragtbrev"),
                }
            )

    def clean_with_formset(self, formset):
        # Perform validation on form and formset together
        if not self.cleaned_data["indførselstilladelse"]:
            # Hvis vi ikke har en indførselstilladelse,
            # tjek om der er nogle varer der kræver det
            for subform in formset:
                if self.varesatser:
                    varesats_id = subform.cleaned_data["vareafgiftssats"]
                    vareafgiftssats = self.varesatser[int(varesats_id)]
                    if vareafgiftssats["kræver_indførselstilladelse"]:
                        self.add_error(
                            "indførselstilladelse",
                            _(
                                "Indførselstilladelse er påkrævet med "
                                "de angivne varearter"
                            ),
                        )
                        break


class TF10VareForm(BootstrapForm):
    def __init__(self, *args, **kwargs):
        self.varesatser = kwargs.pop("varesatser", {})
        super().__init__(*args, **kwargs)
        self.fields["vareafgiftssats"].choices = tuple(
            (id, item["vareart"]) for id, item in self.varesatser.items()
        )

    id = forms.IntegerField(min_value=1, required=False, widget=forms.HiddenInput)
    vareafgiftssats = forms.ChoiceField(choices=())
    mængde = forms.DecimalField(min_value=0, required=False)
    antal = forms.IntegerField(min_value=1, required=False)
    fakturabeløb = forms.DecimalField(min_value=1, decimal_places=2)

    def clean_mængde(self) -> int:
        mængde = self.cleaned_data["mængde"]
        if (
            "vareafgiftssats" in self.cleaned_data
        ):  # If not, it will fail validation elsewhere
            varesats = self.varesatser[int(self.cleaned_data["vareafgiftssats"])]
            if not mængde and varesats["enhed"] in ("kg", "l"):
                raise ValidationError(
                    self.fields["mængde"].error_messages["required"], code="required"
                )
        return mængde

    def clean_antal(self) -> int:
        antal = self.cleaned_data["antal"]
        if (
            "vareafgiftssats" in self.cleaned_data
        ):  # If not, it will fail validation elsewhere
            varesats = self.varesatser[int(self.cleaned_data["vareafgiftssats"])]
            if not antal and varesats["enhed"] == "ant":
                raise ValidationError(
                    self.fields["antal"].error_messages["required"], code="required"
                )
        return antal


TF10VareFormSet = formset_factory(TF10VareForm, min_num=1, extra=0)


class PaginateForm(Form):
    json = forms.BooleanField(required=False)
    offset = forms.IntegerField(required=False)
    limit = forms.IntegerField(required=False)
    sort = forms.CharField(required=False)
    order = forms.CharField(required=False)


class TF10SearchForm(PaginateForm, BootstrapForm):
    def __init__(self, *args, **kwargs):
        self.varesatser = kwargs.pop("varesatser", {})
        self.afsendere = kwargs.pop("afsendere", {})
        self.modtagere = kwargs.pop("modtagere", {})
        super().__init__(*args, **kwargs)

        # We use 'set' here, because one 'vareafgiftssats' can exist in many
        # different tables
        self.fields["vareart"].choices = tuple(
            [(None, "------")]
            + sorted(
                set(
                    [
                        (item["vareart"], item["vareart"].lower().capitalize())
                        for item in self.varesatser.values()
                    ]
                ),
                key=lambda items: items[1],
            )
        )

        self.fields["afsender"].choices = tuple(
            [(None, "------")]
            + sorted(
                [(item["id"], item["navn"]) for item in self.afsendere.values()],
                key=lambda items: items[1],
            )
        )

        self.fields["modtager"].choices = tuple(
            [(None, "------")]
            + sorted(
                [(item["id"], item["navn"]) for item in self.modtagere.values()],
                key=lambda items: items[1],
            )
        )

    vareart = forms.ChoiceField(choices=(), required=False)
    godkendt = forms.ChoiceField(
        choices=(
            (None, _("Alle")),
            (True, _("Godkendt")),
            (False, _("Afvist")),
            ("explicitly_none", _("Ny")),
        ),
        required=False,
        widget=forms.Select(attrs={"onchange": "form.submit();"}),
    )
    godkendt_is_null = forms.ChoiceField(
        choices=(
            (None, _("------")),
            (True, _("Ja")),
            (False, _("Nej")),
        ),
        required=False,
    )

    dato_efter = forms.DateField(required=False, widget=DateInput)
    dato_før = forms.DateField(required=False, widget=DateInput)
    afgangsdato_efter = forms.DateField(required=False, widget=DateInput)
    afgangsdato_før = forms.DateField(required=False, widget=DateInput)
    htmx = forms.BooleanField(required=False)
    order_by = forms.CharField(required=False)

    id = forms.IntegerField(required=False)
    afsender = forms.ChoiceField(required=False)
    modtager = forms.ChoiceField(required=False)

    afsenderbykode_or_forbindelsesnr = forms.CharField(required=False)
    postforsendelsesnummer_or_fragtbrevsnummer = forms.CharField(required=False)
