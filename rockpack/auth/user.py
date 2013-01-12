from flask.ext.login import UserMixin

import models

class User(UserMixin):

    @classmethod
    def get_from_login(cls, username):
        try:
            return models.User.get_from_username(username)
        except models.InvalidUserException:
            raise
