from flask.ext import login
from flask import request
from flask.ext.rauth import RauthOAuth2, RauthResponse, parse_response
from .user import User


# We need to patch RauthResponse because obj.response
# might be a callable which returns a dict (which Rauth
# isn't expecting), so we need to call it if it is
def _patched_content(obj):
        '''
        The content associated with the response. The content is parsed into a
        more useful format, if possible, using :func:`parse_response`.

        The content is cached, so that :func:`parse_response` is only run once.
        '''
        if obj._cached_content is None:
            # the parsed content from the server
            r = parse_response(obj.response)
            if callable(r):
                obj._cached_content = r()
            else:
                obj._cached_content = r
        return obj._cached_content
setattr(RauthResponse, 'content', property(_patched_content))


class GoogleOAuth(RauthOAuth2):
    def __init__(self, key, secret):
        super(GoogleOAuth, self).__init__(
            name='google',
            base_url='https://www.googleapis.com/oauth2/v1/',
            access_token_url='https://accounts.google.com/o/oauth2/token',
            authorize_url='https://accounts.google.com/o/oauth2/auth',
            consumer_key=key,
            consumer_secret=secret,
        )


# Used for auth decoration in views.py
google_oauth = None


class LoginManager(login.LoginManager):
    # Only use login manager on admin requests

    def _load_user(self):
        if request.path.startswith('/admin'):
            return super(LoginManager, self)._load_user()

    def _update_remember_cookie(self, response):
        if request.path.startswith('/admin'):
            return super(LoginManager, self)._update_remember_cookie(response)
        else:
            return response


class AnonymousUser(login.AnonymousUserMixin):
    username = 'guest'


def setup_auth(app):
    global google_oauth
    google_oauth = GoogleOAuth(app.config['GOOGLE_CONSUMER_KEY'],
                               app.config['GOOGLE_CONSUMER_SECRET'])
    login_manager = LoginManager()
    login_manager.setup_app(app)
    login_manager.user_loader(lambda id: User.get_from_login(id))
    login_manager.anonymous_user = AnonymousUser
    login_manager.login_view = '.login'
