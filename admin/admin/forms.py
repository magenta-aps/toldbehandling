from django import forms

from told_common.form_mixins import BootstrapForm


class TF10GodkendForm(BootstrapForm):
    godkendt = forms.BooleanField(required=False)
