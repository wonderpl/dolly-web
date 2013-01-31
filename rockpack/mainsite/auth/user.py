from flask import g
from flask.ext.login import UserMixin

import models


class Admin(UserMixin):
    def __init__(self, id, username, email, active=True):
        self.id = id
        self.username = username
        self.email = email
        self.active = active

        self._roles = g.session.query(models.AdminRole).filter_by(id=self.id)

    @classmethod
    def get_from_token(cls, token):
        try:
            u = models.Admin.get_from_token(token)
        except models.InvalidAdminException:
            return None
        return Admin(u.id, u.username, u.email)

    @classmethod
    def get_from_login(cls, userid):
        try:
            u = models.Admin.get_from_login(userid)
        except models.InvalidAdminException:
            return None
        return Admin(u.id, u.username, u.email)
    
    @classmethod
    def register_token(cls, token, email):
        try:
            u = models.Admin.get_from_email(email)
        except models.InvalidAdminException:
            return None
        else:
            if u.email == email:
                u.token = token
                u.save()
        return Admin(u.id, u.username, u.email)

    def has_permission(self, permission):
        # TODO
        # session.query(models.RolePermissions).filter(models.RolePermissions==permission)
        return True

    def get_id(self):
        return self.id

    def is_active(self):
        return self.active

    def is_authenticated(self):
        return True

    def is_anonymous(self):
        return False
