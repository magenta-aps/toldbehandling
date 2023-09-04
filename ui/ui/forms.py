from django import forms
from django.core.exceptions import ValidationError
from django.forms import formset_factory
from django.utils.translation import gettext_lazy as _
from requests import HTTPError
from told_common.form_mixins import (
    BootstrapForm,
    ButtonlessIntegerField,
    MaxSizeFileField,
    DateInput,
)
from told_common.rest_client import RestClient


class LoginForm(BootstrapForm):
    username = forms.CharField(
        max_length=150, widget=forms.TextInput(attrs={"placeholder": _("Brugernavn")})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": _("Adgangskode")})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = None

    def clean(self):
        try:
            self.token = RestClient.login(
                self.cleaned_data["username"], self.cleaned_data["password"]
            )
        except HTTPError:
            raise ValidationError(_("Login fejlede"))


class TF10Form(BootstrapForm):
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
    modtager_indførselstilladelse = forms.CharField(
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
        required=False,
    )
    fragtbrevnr = forms.CharField(
        required=True,
    )

    def clean(self):
        if self.cleaned_data["fragttype"] in (
            "skibsfragt",
            "luftfragt",
        ) and not self.files.get("fragtbrev"):
            raise ValidationError(
                {
                    "fragtbrev": _("Mangler fragtbrev"),
                }
            )

    def clean_with_formset(self, formset):
        # Perform validation on form and formset together
        pass


class TF10VareForm(BootstrapForm):
    def __init__(self, *args, **kwargs):
        self.varesatser = kwargs.pop("varesatser", {})
        super().__init__(*args, **kwargs)
        self.fields["vareart"].choices = tuple(
            (id, item["vareart"]) for id, item in self.varesatser.items()
        )

    vareart = forms.ChoiceField(choices=())
    mængde = forms.IntegerField(min_value=1, required=False)
    antal = forms.IntegerField(min_value=1, required=False)
    fakturabeløb = forms.DecimalField(min_value=1, decimal_places=2)

    def clean_mængde(self) -> int:
        mængde = self.cleaned_data["mængde"]
        if "vareart" in self.cleaned_data:  # If not, it will fail validation elsewhere
            varesats = self.varesatser[int(self.cleaned_data["vareart"])]
            if not mængde and varesats["enhed"] in ("kg", "l"):
                raise ValidationError(
                    self.fields["mængde"].error_messages["required"], code="required"
                )
        return mængde

    def clean_antal(self) -> int:
        antal = self.cleaned_data["antal"]
        if "vareart" in self.cleaned_data:  # If not, it will fail validation elsewhere
            varesats = self.varesatser[int(self.cleaned_data["vareart"])]
            if not antal and varesats["enhed"] == "ant":
                raise ValidationError(
                    self.fields["antal"].error_messages["required"], code="required"
                )
        return antal


TF10VareFormSet = formset_factory(TF10VareForm, min_num=1, extra=0)


class TF10GodkendForm(BootstrapForm):
    godkend = forms.CharField(required=True)


class TF10SearchForm(BootstrapForm):
    def __init__(self, *args, **kwargs):
        self.varesatser = kwargs.pop("varesatser", {})
        super().__init__(*args, **kwargs)
        self.fields["vareart"].choices = tuple(
            [(None, "------")]
            + [(id, item["vareart"]) for id, item in self.varesatser.items()]
        )

    vareart = forms.ChoiceField(choices=(), required=False)
    dato_efter = forms.DateField(required=False, widget=DateInput)
    dato_før = forms.DateField(required=False, widget=DateInput)
    json = forms.BooleanField(required=False)
    htmx = forms.BooleanField(required=False)
    order_by = forms.CharField(required=False)
    offset = forms.IntegerField(required=False)
    limit = forms.IntegerField(required=False)

    sort = forms.CharField(required=False)
    order = forms.CharField(required=False)
