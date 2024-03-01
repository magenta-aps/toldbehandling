from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from two_factor.utils import default_device
from two_factor.views import LoginView, SetupView

from told_common import views as common_views
from told_common.form_mixins import BootstrapForm
from told_twofactor import forms
from two_factor.views.utils import class_view_decorator


# @class_view_decorator(login_required(reverse_lazy("twofactor:base_login")))
class TwoFactorSetupView(SetupView):
    form_list = [("method", forms.AuthenticationTokenForm)]
    template_name = 'told_twofactor/setup.html'


    # def get_success_url(self):
    #     return (reverse("login", kwargs={"pk": self.request.user.id}) +
    #             "?two_factor_success=1")

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form, **kwargs)
        context.pop('cancel_url')
        return context

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        BootstrapForm.apply_field_classes(form)
        return form


class TwofactorLoginView(LoginView):
    form_class = forms.TwofactorLoginForm
