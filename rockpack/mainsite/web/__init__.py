from flask.ext.assets import Environment
# Init app routes
from .views import homepage


def setup_web(app):
    env = Environment(app)
