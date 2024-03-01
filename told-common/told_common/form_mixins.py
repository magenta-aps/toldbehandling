# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import re
from typing import Optional

from django import forms
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.validators import MaxValueValidator, MinValueValidator
from django.forms import FileField, MultipleChoiceField, Form
from django.utils.translation import gettext_lazy as _
from dynamic_forms import DynamicFormMixin
from humanize import naturalsize


class BootstrapForm(DynamicFormMixin, forms.Form):
    def __init__(self, *args, **kwargs):
        print("BootstrapForm init")
        super(BootstrapForm, self).__init__(*args, **kwargs)
        self.kwargs = kwargs
        for name, field in self.fields.items():
            self.update_field(name, field)
            self.set_field_classes(self, name, field)

    def full_clean(self):
        result = super(BootstrapForm, self).full_clean()
        self.set_all_field_classes()
        return result

    def set_all_field_classes(self):
        self.apply_field_classes(self)

    @classmethod
    def apply_field_classes(cls, form: Form):
        for name, field in form.fields.items():
            print(name)
            cls.set_field_classes(form, name, field, True)

    @classmethod
    def set_field_classes(cls, form, name, field, check_for_errors=False):
        classes = BootstrapForm.split_class(field.widget.attrs.get("class"))
        classes.append("mr-2")
        if isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect)):
            pass
        else:
            classes.append("form-control")
            if isinstance(field.widget, forms.Select):
                classes.append("form-select")

        if check_for_errors:
            if form.has_error(name) is True:
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


class ButtonlessDecimalField(ErrorMessagesFieldMixin, forms.DecimalField):
    widget = forms.NumberInput(attrs={"class": "no-buttons"})
    attribute_map = {
        "min_value": "data-validity-rangeunderflow",
        "max_value": "data-validity-rangeoverflow",
    }


class FixedWidthIntegerField(ErrorMessagesFieldMixin, forms.CharField):
    widget = forms.TextInput()
    attribute_map = {
        "min_value": "data-validity-rangeunderflow",
        "max_value": "data-validity-rangeoverflow",
    }
    default_error_messages = {
        "invalid": _(
            "Indtast et heltal, evt. med foranstillede nuller"
        ),  # Kopieret fra Django
    }

    def __init__(self, width: int = 1, min_value: int = 0, *args, widget_attrs=None, **kwargs):
        self.width = int(width)
        self.min_value = int(min_value)
        self.extra_widget_attrs = widget_attrs
        super().__init__(*args, **kwargs)
        self.validators.append(MinValueValidator(min_value))
        self.validators.append(MaxValueValidator((10**width) - 1))

    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        # HTML-attributter. Hvis vi havde sat max_length og min_length
        # på `CharField`, var der kommet strengvalidatorer som kører
        # på vores konverterede int-værdi fra `to_python`
        attrs["maxlength"] = str(self.width)
        attrs["minlength"] = str(self.width)
        attrs["pattern"] = "\\d{" + str(self.width) + "}"
        if type(self.extra_widget_attrs) is dict:
            attrs.update(self.extra_widget_attrs)
        return attrs

    def to_python(self, value: str) -> Optional[int]:
        # Fra formularfeltets value til python-værdi
        # Validering kører på returværdien
        value = super().to_python(value)
        if value in (None, ""):
            return None
        try:
            return int(value)
        except ValueError:
            raise ValidationError(self.error_messages["invalid"], code="invalid")

    def prepare_value(self, value: Optional[int]) -> str:
        # Fra python-værdi til formularfeltets value
        if value is None:
            return ""
        return str(value).zfill(self.width)


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
