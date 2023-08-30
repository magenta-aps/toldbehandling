from django import forms


class BootstrapForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(BootstrapForm, self).__init__(*args, **kwargs)
        for name, field in self.fields.items():
            self.set_field_classes(name, field)
            self.update_field(name, field)

    def full_clean(self):
        result = super(BootstrapForm, self).full_clean()
        for name, field in self.fields.items():
            self.set_field_classes(name, field, True)

        return result

    def set_field_classes(self, name, field, check_for_errors=False):
        classes = self.split_class(field.widget.attrs.get("class"))
        classes.append("mr-2")
        # if isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect)):
        #    if "not-form-check-input" not in classes:
        #        classes.append("form-check-input")
        # else:
        classes.append("form-control")

        if check_for_errors:
            if self.has_error(name) is True:
                print(f"{name} has error")
                classes.append("is-invalid")
        field.widget.attrs["class"] = " ".join(set(classes))

    @staticmethod
    def split_class(class_string):
        return class_string.split(" ") if class_string else []

    def update_field(self, name, field):
        if isinstance(field.widget, forms.FileInput):
            field.widget.template_name = "widgets/file.html"
            field.widget.attrs["class"] = "custom-file-input"
