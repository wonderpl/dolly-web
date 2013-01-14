from flask.ext.login import UserMixin

import models

class User(UserMixin):
    def __init(self, dbuser):
        self._user = dbuser

    @classmethod
    def get_from_tokenn(cls, token):
        u = models.User.get_from_token(token)

        return User(u)

    @classmethod
    def get_from_login(cls, userid):
        u = models.User.get_from_login(userid)

        return User(u)
        """
        try:
            return models.User.get_from_username(username)
        except models.InvalidUserException:
            raise
        """

    def get_id(self):
        return unicode(self._user.username)
