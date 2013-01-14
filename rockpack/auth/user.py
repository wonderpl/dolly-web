from flask.ext.login import UserMixin

import models

class User(UserMixin):
    def __init__(self, id, username, email, active=True):
        self.id = id
        self.username = username
        self.email = email
        self.active = active

    @classmethod
    def get_from_token(cls, token):
        try:
            u = models.User.get_from_token(token)
        except models.InvalidUserException:
            return None
        return User(u.id, u.username, u.email)

    @classmethod
    def get_from_login(cls, userid):
        try:
            u = models.User.get_from_login(userid)
        except models.InvalidUserException:
            return None
        return User(u.id, u.username, u.email)
    
    @classmethod
    def register_token(cls, token, email):
        try:
            u = models.User.get_from_email(email)
        except models.InvalidUserException:
            return None
        else:
            if u.email == email:
                u.token = token
                u.save()
        return User(u.id, u.username, u.email)

    def get_id(self):
        return self.id

    def is_active(self):
        return self.active

    def is_authenticated(self):
        return True

    def is_anonymous(self):
        return False
