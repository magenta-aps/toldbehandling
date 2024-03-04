from django.contrib.auth.backends import ModelBackend
from django_otp import verify_token
from django_otp.plugins.otp_totp.models import TOTPDevice


class AuthenticationBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        user = super().authenticate(request, username, password, **kwargs)
        twofactor_token = kwargs.get("twofactor_token")
        if twofactor_token is None:
            return
        for device in TOTPDevice.objects.filter(user=user):
            accepting_device = verify_token(user, device, twofactor_token)
            if accepting_device:
                return user
