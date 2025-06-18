from django.utils.translation import gettext_lazy as _
from two_factor.plugins import registry as twofactor_registry


class GeneratorMethod(twofactor_registry.GeneratorMethod):
    form_path = "told_twofactor.forms.TOTPDeviceForm"
    code = "generator"

    def get_setup_forms(self, *args):
        from told_twofactor.forms import TOTPDeviceForm

        return {"generator": TOTPDeviceForm}


def update_registry():
    twofactor_registry.registry.unregister("generator")
    twofactor_registry.registry.register(GeneratorMethod())
