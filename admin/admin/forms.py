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
