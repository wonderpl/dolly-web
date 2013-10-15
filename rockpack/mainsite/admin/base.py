from flask.ext import login
from flask.ext.admin import BaseView


class AuthenticatedView(BaseView):

    def is_authenticated(self):
        return login.current_user.is_authenticated()

    def is_accessible(self):
        return self.is_authenticated()
