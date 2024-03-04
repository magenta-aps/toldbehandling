import time
from collections import OrderedDict

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.exceptions import SuspiciousOperation
from django.shortcuts import redirect
from django.urls import reverse
from django_otp.plugins.otp_static.models import StaticDevice
from formtools.wizard.forms import ManagementForm
from told_common import forms as common_forms
from told_common import views as common_views
from told_common.view_mixins import HasRestClientMixin, HasSystemRestClientMixin
from told_twofactor import forms
from told_twofactor.registry import update_registry
from two_factor import forms as twofactor_forms
from two_factor import views as twofactor_views
from two_factor.utils import USER_DEFAULT_DEVICE_ATTR_NAME, default_device
from told_common.rest_client import RestClient

update_registry()



# @class_view_decorator(login_required(reverse_lazy("twofactor:base_login")))
class TwoFactorSetupView(HasRestClientMixin, twofactor_views.SetupView):
    form_list = [("method", forms.AuthenticationTokenForm)]
    template_name = 'told_twofactor/setup.html'

    def get_success_url(self):
        return (reverse("login", kwargs={"pk": self.request.user.id}) +
                "?two_factor_success=1")

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form, **kwargs)
        context.pop('cancel_url')
        return context

    def get_form_kwargs(self, step=None):
        # Overstyring så vi kan sende viewet over i formularen
        kwargs = super().get_form_kwargs(step)
        kwargs["view"] = self
        return kwargs


class TwofactorLoginView(HasRestClientMixin, common_views.LoginView):
    form_class = forms.TwofactorLoginForm
    template_name = "told_twofactor/login.html"

    def form_valid(self, form):
        form.token.save(self.request, save_refresh_token=True)
        userdata = RestClient(form.token).user.this()
        self.request.session["user"] = userdata
        return super().form_valid(form)



#
# class TwofactorLoginView(HasSystemRestClientMixin, twofactor_views.LoginView):
#     form_list = (
#         (twofactor_views.LoginView.AUTH_STEP, common_forms.LoginForm),
#         (twofactor_views.LoginView.TOKEN_STEP, twofactor_forms.AuthenticationTokenForm),
#         (twofactor_views.LoginView.BACKUP_STEP, twofactor_forms.BackupTokenForm),
#     )
#     # form_class = forms.TwofactorLoginForm
#     template_name = "told_twofactor/login.html"
#     storage_name = 'told_twofactor.utils.LoginStorage'
#
#     def get_success_url(self):
#         next = self.request.GET.get("back") or self.request.GET.get(REDIRECT_FIELD_NAME)
#         if next:
#             return next
#
#     #--------------------------------
#
#     def process_step(self, form):
#         print("process_step")
#         """
#         Process an individual step in the flow
#         """
#         # To prevent saving any private auth data to the session store, we
#         # validate the authentication form, determine the resulting user, then
#         # only store the minimum needed to login that user (the user's primary
#         # key and the backend used)
#         if self.steps.current == self.AUTH_STEP:
#             print("auth step")
#             user = form.is_valid() and form.user_cache
#             print(f"user: {user}")
#             self.storage.reset()
#             self.storage.authenticated_user = user
#             self.storage.data["authentication_time"] = int(time.time())
#
#             # By returning None when the user clicks the "back" button to the
#             # auth step the form will be blank with validation warnings
#             return None
#
#         return super().process_step(form)
#
#     def default_device(self, user):
#         print("default_device")
#
#         if not user or user.is_anonymous:
#             print("no user")
#             return
#         if hasattr(user, USER_DEFAULT_DEVICE_ATTR_NAME):
#             print(getattr(user, USER_DEFAULT_DEVICE_ATTR_NAME))
#             return getattr(user, USER_DEFAULT_DEVICE_ATTR_NAME)
#         devices = self.rest_client.totpdevice.get_for_user(user)
#         print(devices)
#         for device in devices:
#             if device.name == 'default':
#                 setattr(user, USER_DEFAULT_DEVICE_ATTR_NAME, device)
#                 print("got default device")
#                 return device
#         return None
#
#     def get_device(self, step=None):
#         """
#         Returns the OTP device selected by the user, or his default device.
#         """
#         if not self.device_cache:
#             challenge_device_id = (
#                     self.request.POST.get('challenge_device')
#                     or self.storage.data.get('challenge_device')
#             )
#             if challenge_device_id:
#                 for device in self.get_devices():
#                     if device.persistent_id == challenge_device_id:
#                         self.device_cache = device
#                         break
#
#             # if step == self.BACKUP_STEP:
#             #     try:
#             #         self.device_cache = self.get_user().staticdevice_set.get(name='backup')
#             #     except StaticDevice.DoesNotExist:
#             #         pass
#
#             if not self.device_cache:
#                 self.device_cache = default_device(self.get_user())
#
#         return self.device_cache
#
#
#     def get_user(self):
#         """
#         Returns the user authenticated by the AuthenticationForm. Returns False
#         if not a valid user; see also issue #65.
#         """
#         if not self.user_cache:
#             print(self.storage.authenticated_user)
#             self.user_cache = self.storage.authenticated_user
#         return self.user_cache
#
#     # def has_token_step(self):
#     #     print(self.get_user())
#     #     x = (
#     #             self.default_device(self.get_user()) and
#     #             not self.remember_agent
#     #     )
#     #     print(f"has_token_step: {x}")
#     #     return x
#
#     condition_dict = {
#         twofactor_views.LoginView.TOKEN_STEP: False,
#         twofactor_views.LoginView.BACKUP_STEP: False,
#     }
#
#     def post(self, *args, **kwargs):
#
#         management_form = ManagementForm(self.request.POST, prefix=self.prefix)
#         if not management_form.is_valid():
#             raise SuspiciousOperation('ManagementForm data is missing or has been tampered.')
#         print(management_form.cleaned_data)
#
#         return super().post(*args, **kwargs)
#
#
#     def done(self, form_list, **kwargs):
#         print("DONE")
#         # current_step_data = self.storage.get_step_data(self.steps.current)
#         # remember = bool(current_step_data and current_step_data.get('token-remember') == 'on')
#         redirect_to = self.get_success_url()
#         return redirect(redirect_to)
#
#
#
