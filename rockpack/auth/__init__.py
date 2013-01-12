from flask.ext import login

from views import load_user
from views import login_view
from views import logout

def setup_auth(app):
    login_manager = login.LoginManager()
    login_manager.setup_app(app)
    login_manager.user_loader(load_user)
    login_manager.login_view = 'login'

    app.add_url_rule('/login/', 'login', login_view, methods=('GET', 'POST'))
    app.add_url_rule('/logout/', 'logout', logout)
