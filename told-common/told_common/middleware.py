from django.contrib.auth.models import AnonymousUser
from django.utils.deprecation import MiddlewareMixin
from told_common.data import JwtTokenInfo, User


class RestTokenUser:
    def __init__(self, userdata: User, jwt_token: JwtTokenInfo):
        super().__init__()
        self.userdata = userdata
        self.jwt_token = jwt_token


class RestTokenUserMiddleware(MiddlewareMixin):
    def process_request(self, request, *args, **kwargs):
        self.set_user(request)

    @staticmethod
    def set_user(request):
        if "user" in request.session:
            try:
                request.user = User.from_dict(
                    {
                        **request.session.get("user"),
                        "jwt_token": JwtTokenInfo.load(request),
                    }
                )
            except KeyError:
                print(
                    {
                        **request.session.get("user"),
                        "jwt_token": JwtTokenInfo.load(request),
                    }
                )
                raise
        else:
            # request.user = User(None, None)
            request.user = AnonymousUser()
