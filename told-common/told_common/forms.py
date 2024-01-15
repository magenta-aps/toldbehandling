# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0
from datetime import date
from decimal import Decimal
from typing import Iterable, Optional

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.forms import CharField, Form, formset_factory
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from dynamic_forms import DynamicField
from requests import HTTPError
from told_common.data import Vareafgiftssats
from told_common.form_mixins import (
    BootstrapForm,
    ButtonlessIntegerField,
    DateInput,
    MaxSizeFileField,
)
from told_common.rest_client import RestClient
from told_common.util import cast_or_none, date_next_workdays


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
        self.varesatser = varesatser
        self.leverandørfaktura_required = leverandørfaktura_required
        self.fragtbrev_required = fragtbrev_required
        super().__init__(*args, **kwargs)

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
    indførselstilladelse = DynamicField(
        forms.CharField,
        max_length=12,
        required=False,
        label=_("Indførsels­tilladelse nr."),
        widget=lambda form: forms.TextInput(
            attrs={
                "data-required-field": "[name$=vareafgiftssats]",
                "data-required-values": ",".join(
                    [
                        str(id)
                        for id, sats in form.varesatser.items()
                        if sats.kræver_indførselstilladelse
                    ]
                ),
            }
            if form.varesatser
            else {}
        ),
    )
    leverandørfaktura_nummer = forms.CharField(
        label=_("Leverandør­faktura nr."),
        max_length=20,
        required=True,
    )
    leverandørfaktura = DynamicField(
        MaxSizeFileField,
        allow_empty_file=False,
        label=_("Leverandør­faktura"),
        max_size=10000000,
        required=lambda form: bool(form.leverandørfaktura_required),
    )
    fragtbrev = DynamicField(
        MaxSizeFileField,
        allow_empty_file=False,
        label=_("Fragtbrev"),
        max_size=10000000,
        required=False,
        widget_attrs=lambda form: {
            "data-required-field": "[name=fragttype]",
            "data-required-values": "skibsfragt,luftfragt",
        }
        if form.fragtbrev_required
        else None,
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
    modtager_betaler = forms.BooleanField(
        label=_("Betales af"),
        required=False,
        widget=forms.Select(
            choices=(
                (True, _("Modtager")),
                (False, _("Afsender")),
            )
        ),
    )
    afgangsdato = forms.DateField(
        required=True,
        widget=DateInput(),
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
                    if vareafgiftssats.kræver_indførselstilladelse:
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
        vareart_key = (
            "vareart_kl" if translation.get_language() == "kl" else "vareart_da"
        )
        self.varesatser_choices = tuple(
            (id, getattr(item, vareart_key)) for id, item in self.varesatser.items()
        )
        super().__init__(*args, **kwargs)

    id = forms.IntegerField(min_value=1, required=False, widget=forms.HiddenInput)
    vareafgiftssats = DynamicField(
        forms.ChoiceField, choices=lambda form: form.varesatser_choices
    )
    mængde = forms.DecimalField(min_value=0, required=False)
    antal = forms.IntegerField(min_value=1, required=False)
    fakturabeløb = forms.DecimalField(min_value=1, decimal_places=2, required=False)

    def clean_mængde(self) -> int:
        mængde = self.cleaned_data["mængde"]
        if (
            "vareafgiftssats" in self.cleaned_data
        ):  # If not, it will fail validation elsewhere
            varesats = self.varesatser[int(self.cleaned_data["vareafgiftssats"])]
            if not mængde and varesats.enhed in (
                Vareafgiftssats.Enhed.KILOGRAM,
                Vareafgiftssats.Enhed.LITER,
            ):
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
            if not antal and varesats.enhed == Vareafgiftssats.Enhed.ANTAL:
                raise ValidationError(
                    self.fields["antal"].error_messages["required"], code="required"
                )
        return antal

    def clean_fakturabeløb(self) -> Optional[Decimal]:
        fakturabeløb = self.cleaned_data["fakturabeløb"]
        if (
            "vareafgiftssats" in self.cleaned_data
        ):  # If not, it will fail validation elsewhere
            varesats = self.varesatser[int(self.cleaned_data["vareafgiftssats"])]
            if not fakturabeløb and varesats.enhed in (
                Vareafgiftssats.Enhed.PROCENT,
                Vareafgiftssats.Enhed.SAMMENSAT,
            ):
                raise ValidationError(
                    self.fields["fakturabeløb"].error_messages["required"],
                    code="required",
                )
        return cast_or_none(Decimal, fakturabeløb)


TF10VareFormSet = formset_factory(TF10VareForm, min_num=1, extra=0)


class PaginateForm(Form):
    json = forms.BooleanField(required=False)
    offset = forms.IntegerField(required=False)
    limit = forms.IntegerField(required=False)
    sort = forms.CharField(required=False)
    order = forms.CharField(required=False)


def vareart_choices(varesatser: Iterable[Vareafgiftssats]):
    vareart_key = "vareart_kl" if translation.get_language() == "kl" else "vareart_da"
    return tuple(
        [(None, "------")]
        + sorted(
            set(
                [
                    (
                        getattr(item, vareart_key),
                        getattr(item, vareart_key).lower().capitalize(),
                    )
                    for item in varesatser
                ]
            ),
            key=lambda items: items[1],
        )
    )


class TF10SearchForm(PaginateForm, BootstrapForm):
    def __init__(self, *args, **kwargs):
        self.varesatser = kwargs.pop("varesatser", {})
        self.afsendere = kwargs.pop("afsendere", {})
        self.modtagere = kwargs.pop("modtagere", {})
        super().__init__(*args, **kwargs)

    vareart = DynamicField(
        forms.ChoiceField,
        choices=lambda form: vareart_choices(form.varesatser.values()),
        required=False,
    )
    status = forms.ChoiceField(
        choices=(
            (None, _("Alle")),
            ("ny", _("Ny")),
            ("afvist", _("Afvist")),
            ("godkendt", _("Godkendt")),
            ("afsluttet", _("Sendt til Prisme")),
        ),
        required=False,
        widget=forms.Select(attrs={"onchange": "form.submit();"}),
    )

    dato_efter = forms.DateField(required=False, widget=DateInput)
    dato_før = forms.DateField(required=False, widget=DateInput)
    afgangsdato_efter = forms.DateField(required=False, widget=DateInput)
    afgangsdato_før = forms.DateField(required=False, widget=DateInput)
    htmx = forms.BooleanField(required=False)
    order_by = forms.CharField(required=False)

    id = forms.IntegerField(required=False)
    afsender = DynamicField(
        forms.ChoiceField,
        required=False,
        choices=lambda form: tuple(
            [(None, "------")]
            + sorted(
                [(item["id"], item["navn"]) for item in form.afsendere.values()],
                key=lambda items: items[1],
            )
        ),
    )
    modtager = DynamicField(
        forms.ChoiceField,
        required=False,
        choices=lambda form: tuple(
            [(None, "------")]
            + sorted(
                [(item["id"], item["navn"]) for item in form.modtagere.values()],
                key=lambda items: items[1],
            )
        ),
    )

    afsenderbykode_or_forbindelsesnr = forms.CharField(required=False)
    postforsendelsesnummer_or_fragtbrevsnummer = forms.CharField(required=False)


class TF5SearchForm(PaginateForm, BootstrapForm):
    def __init__(self, *args, **kwargs):
        self.varesatser = kwargs.pop("varesatser", {})
        super().__init__(*args, **kwargs)

    vareart = DynamicField(
        forms.ChoiceField,
        choices=lambda form: vareart_choices(form.varesatser.values()),
        required=False,
    )
    # status = forms.ChoiceField(
    #     choices=(
    #         (None, _("Alle")),
    #         ("ny", _("Ny")),
    #         ("afvist", _("Afvist")),
    #         ("godkendt", _("Godkendt")),
    #         ("afsluttet", _("Afsluttet")),
    #     ),
    #     required=False,
    #     widget=forms.Select(attrs={"onchange": "form.submit();"}),
    # )
    leverandørfaktura_nummer = forms.CharField(required=False)

    afgangsdato_efter = forms.DateField(required=False, widget=DateInput)
    afgangsdato_før = forms.DateField(required=False, widget=DateInput)
    oprettet_efter = forms.DateField(required=False, widget=DateInput)
    oprettet_før = forms.DateField(required=False, widget=DateInput)

    order_by = forms.CharField(required=False)

    id = forms.IntegerField(required=False)


class TF5ViewForm(BootstrapForm):
    annulleret = forms.BooleanField(required=False)
    # For at vi kan have tre formfelter i hver sin modal
    notat1 = forms.CharField(
        widget=forms.Textarea(
            attrs={"placeholder": _("Notat"), "disabled": "disabled"}
        ),
        required=False,
    )


class TF5Form(BootstrapForm):
    def __init__(
        self,
        leverandørfaktura_required: bool = True,
        varesatser: Optional[dict] = None,
        *args,
        **kwargs,
    ):
        self.leverandørfaktura_required = leverandørfaktura_required
        self.varesatser = varesatser
        super().__init__(*args, **kwargs)
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
    leverandørfaktura = DynamicField(
        MaxSizeFileField,
        allow_empty_file=False,
        label=_("Vare­faktura"),
        max_size=10000000,
        required=lambda form: form.leverandørfaktura_required,
        widget=forms.widgets.ClearableFileInput(
            attrs={
                "data-tooltip-title": _("Varefaktura"),
                "data-tooltip-content": _("Vedhæftning af varefaktura"),
                "accept": ".pdf,application/pdf",
            }
        ),
    )
    indleveringsdato = DynamicField(
        forms.DateField,
        label=_("Dato for indlevering til forsendelse"),
        required=True,
        widget=lambda form: DateInput(
            attrs={"min": date_next_workdays(date.today(), 6)}
        ),
    )
    anonym = forms.BooleanField(
        required=False,
    )
    betal = forms.BooleanField(required=False)
