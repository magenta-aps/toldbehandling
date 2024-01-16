# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import re

from django import forms
from django.core.files import File
from django.forms import FileField, MultipleChoiceField
from django.utils.translation import gettext_lazy as _
from dynamic_forms import DynamicFormMixin
from humanize import naturalsize


class BootstrapForm(DynamicFormMixin, forms.Form):
    def __init__(self, *args, **kwargs):
        super(BootstrapForm, self).__init__(*args, **kwargs)
        for name, field in self.fields.items():
            self.update_field(name, field)
            self.set_field_classes(name, field)

    def full_clean(self):
        result = super(BootstrapForm, self).full_clean()
        self.set_all_field_classes()
        return result

    def set_all_field_classes(self):
        for name, field in self.fields.items():
            self.set_field_classes(name, field, True)

    def set_field_classes(self, name, field, check_for_errors=False):
        classes = self.split_class(field.widget.attrs.get("class"))
        classes.append("mr-2")
        if isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect)):
            pass
        else:
            classes.append("form-control")
            if isinstance(field.widget, forms.Select):
                classes.append("form-select")

        if check_for_errors:
            if self.has_error(name) is True:
                classes.append("is-invalid")
        field.widget.attrs["class"] = " ".join(set(classes))

    @staticmethod
    def split_class(class_string):
        return class_string.split(" ") if class_string else []

    def update_field(self, name, field):
        if isinstance(field.widget, forms.FileInput):
            field.widget.template_name = "told_common/widgets/file.html"
            if "class" not in field.widget.attrs:
                field.widget.attrs["class"] = ""
            field.widget.attrs["class"] += " custom-file-input"


class ErrorMessagesFieldMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Tilføj html-attributter på elementet som definerer fejlbeskeder
        # de samles op af javascript og bruges til klientside-validering
        for key, value in self.error_messages.items():
            if key in self.attribute_map:
                html_attr = self.attribute_map[key]
                value = re.sub(
                    r"%\((\w+)\)[s|d]",
                    lambda x: getattr(self, x.group(1), x.group(1)),
                    str(value),
                )
                self.widget.attrs[html_attr] = value


class ButtonlessIntegerField(ErrorMessagesFieldMixin, forms.IntegerField):
    widget = forms.NumberInput(attrs={"class": "no-buttons"})
    attribute_map = {
        "min_value": "data-validity-rangeunderflow",
        "max_value": "data-validity-rangeoverflow",
    }


class MaxSizeFileField(ErrorMessagesFieldMixin, FileField):
    default_error_messages = {
        "max_size": _("Filen er for stor; den må max. være %(max_size_natural)s"),
    }
    attribute_map = {
        "max_size": "data-validity-sizeoverflow",
    }

    def __init__(self, *args, max_size=0, widget_attrs=None, **kwargs):
        self.max_size = max_size
        self.max_size_natural = str(naturalsize(max_size))
        super().__init__(*args, **kwargs)
        self.widget.attrs["max_size"] = max_size
        if widget_attrs:
            self.widget.attrs.update(widget_attrs)

    def clean(self, *args, **kwargs):
        data = super().clean(*args, **kwargs)
        if isinstance(data, File):
            if data.size > self.max_size:
                raise forms.ValidationError(
                    self.error_messages["max_size"],
                    "max_size",
                    {"max_size_natural": self.max_size_natural},
                )
        return data


class DateInput(forms.DateInput):
    input_type = "date"

    def __init__(self, **kwargs):
        kwargs["format"] = "%Y-%m-%d"
        super().__init__(**kwargs)


class DateTimeInput(forms.DateTimeInput):
    input_type = "datetime-local"

    def __init__(self, **kwargs):
        kwargs["format"] = "%Y-%m-%dT%H:%M:%S"
        super().__init__(**kwargs)


class MultipleSeparatedChoiceField(MultipleChoiceField):
    widget = forms.TextInput()

    def __init__(self, delimiters=",", **kwargs):
        self.delimiters = delimiters if type(delimiters) is list else [delimiters]
        super().__init__(**kwargs)
        example = self.delimiters[0].join([label for label, value in self.choices[0:3]])
        self.widget.attrs["placeholder"] = f"f.eks.: {example}"

    def to_python(self, value):
        if not value:
            return []
        return re.split("|".join(map(re.escape, self.delimiters)), value)
