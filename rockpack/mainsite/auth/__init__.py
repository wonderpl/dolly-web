
from flask.ext import login

from views import logout_view
from views import login_view
from views import load_user
from views import authorised
from views import google

def setup_auth(app):
    app.config.update(
        GOOGLE_CONSUMER_KEY='your_conumser_key', # set these up from config
        GOOGLE_CONSUMER_SECRET='your_conumser_secret',
        SECRET_KEY='just a secret key, to confound the bad guys',
        DEBUG=True
    )
    google.init_app(app)
    login_manager = login.LoginManager()
    login_manager.setup_app(app)
    login_manager.user_loader(load_user)
    login_manager.anonymous_user = login.AnonymousUser
    login_manager.login_view = '.login'

    app.add_url_rule('/login/', 'login', login_view)
    app.add_url_rule('/logout/', 'logout', logout_view)
    app.add_url_rule('/authorised', 'authorised', authorised)


