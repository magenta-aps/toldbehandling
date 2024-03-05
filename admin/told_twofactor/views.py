from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.shortcuts import redirect
from django.views.generic import FormView
from told_common.view_mixins import HasRestClientMixin
from told_twofactor import forms
from told_twofactor.registry import update_registry
from two_factor import views as twofactor_views

update_registry()


class TwoFactorSetupView(HasRestClientMixin, twofactor_views.SetupView):
    form_list = [("method", forms.AuthenticationTokenForm)]
    template_name = "told_twofactor/setup.html"

    def get_success_url(self):
        next = self.request.GET.get("back") or self.request.GET.get(REDIRECT_FIELD_NAME)
        if next:
            return next
        return settings.LOGIN_REDIRECT_URL

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form, **kwargs)
        context.pop("cancel_url")
        return context

    def get_form_kwargs(self, step=None):
        # Overstyring så vi kan sende viewet over i formularen
        kwargs = super().get_form_kwargs(step)
        kwargs["view"] = self
        return kwargs

    def done(self, form_list, **kwargs):
        super().done(form_list, **kwargs)
        self.request.session["twofactor_authenticated"] = True
        return redirect(self.get_success_url())


class TwofactorLoginView(HasRestClientMixin, FormView):
    form_class = forms.TwofactorLoginForm
    template_name = "told_twofactor/login.html"

    def get_success_url(self):
        next = self.request.GET.get("back") or self.request.GET.get(REDIRECT_FIELD_NAME)
        if next:
            return next
        return settings.LOGIN_REDIRECT_URL

    def form_valid(self, form):
        self.request.session["twofactor_authenticated"] = True
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user_id"] = self.request.user.id
        return kwargs
