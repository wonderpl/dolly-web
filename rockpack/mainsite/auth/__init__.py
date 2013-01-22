from flask.ext import login
from flask.ext.rauth import RauthOAuth2
from . import patching


patching.patch_rauth()


# Used for auth decoration in views.py
google_oauth = None


def setup_auth(app):
    global google_oauth
    google_oauth = RauthOAuth2(
        name='google',
        base_url='https://www.googleapis.com/oauth2/v1/',
        access_token_url='https://accounts.google.com/o/oauth2/token',
        authorize_url='https://accounts.google.com/o/oauth2/auth',
        consumer_key=app.config['GOOGLE_CONSUMER_KEY'],
        consumer_secret=app.config['GOOGLE_CONSUMER_SECRET'],
    )

    # imported here to avoid circular dependency with google_oauth decorator
    from .views import logout_view, login_view, load_user, authorised

    app.add_url_rule('/login/', 'login', login_view)
    app.add_url_rule('/logout/', 'logout', logout_view)
    app.add_url_rule('/oauth2callback', 'oauth2callback', authorised)
    login_manager = login.LoginManager()
    login_manager.setup_app(app)
    login_manager.user_loader(load_user)
    login_manager.anonymous_user = login.AnonymousUser
    login_manager.login_view = '.login'
