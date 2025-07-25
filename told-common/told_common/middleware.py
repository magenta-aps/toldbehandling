from django.contrib.auth.models import AnonymousUser
from django.utils.deprecation import MiddlewareMixin
from told_common.data import JwtTokenInfo, User


class RestTokenUserMiddleware(MiddlewareMixin):
    def process_request(self, request, *args, **kwargs):
        self.set_user(request)

    @staticmethod
    def set_user(request):
        if "user" in request.session:
            request.user = User.from_dict(
                {
                    **request.session.get("user"),
                    "jwt_token": JwtTokenInfo.load(request),
                }
            )
        else:
            request.user = AnonymousUser()
