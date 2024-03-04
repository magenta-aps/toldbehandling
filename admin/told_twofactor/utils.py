import dataclasses

from told_common.data import User
from two_factor.views.utils import ExtraSessionStorage


class LoginStorage(ExtraSessionStorage):
    """
    SessionStorage that includes the property 'authenticated_user' for storing
    backend authenticated users while logging in.
    """
    def _get_authenticated_user(self):
        if not self.data.get("user"):
            print("GET USER (None)")
            return None
        print("GET USER")
        return User.from_dict(self.data["user"])

    def _set_authenticated_user(self, user: User):
        self.data["user"] = dataclasses.asdict(user)
        print("SET USER")

    authenticated_user = property(_get_authenticated_user, _set_authenticated_user)
