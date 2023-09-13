from django import forms

from told_common.form_mixins import BootstrapForm


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
