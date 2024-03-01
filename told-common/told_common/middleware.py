from django.utils.deprecation import MiddlewareMixin

from told_common.data import User
from told_common.rest_client import JwtTokenInfo


class RestTokenUser:
    def __init__(self, userdata: User, jwt_token: JwtTokenInfo):
        super().__init__()
        self.userdata = userdata
        self.jwt_token = jwt_token


    @property
    def is_authenticated(self):
        return self.jwt_token is not None

    @property
    def is_anonymous(self):
        return self.is_authenticated

    def get_username(self):
        return self.userdata.username

class RestTokenUserMiddleware(MiddlewareMixin):
    def process_request(self, request, *args, **kwargs):
        self.set_user(request)

    @staticmethod
    def set_user(request):
        if "user" in request.session:
            request.user = RestTokenUser(User.from_dict(request.session.get("user")), JwtTokenInfo.load(request))
        else:
            request.user = RestTokenUser(None, None)
            # request.user = AnonymousUser
