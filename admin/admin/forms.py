from datetime import date, timedelta

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from told_common.form_mixins import BootstrapForm, DateInput


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
        required=True, choices=((True, _("Ja")), (False, _("Nej")))
    )
    gyldig_fra = forms.DateField(
        required=True,
        widget=DateInput(attrs={"min": (date.today() + timedelta(1)).isoformat()}),
    )

    def clean(self, *args, **kwargs):
        data = super().clean(*args, **kwargs)
        return data

    def clean_gyldig_fra(self):
        value = self.cleaned_data["gyldig_fra"]
        if value <= date.today():
            raise ValidationError(_("Dato skal være efter i dag"))
        return value
