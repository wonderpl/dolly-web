from flask.ext.assets import Environment
import rockpack.mainsite.web.filters.angulartemplates

# Init app routes
from .views import homepage

def setup_web(app):
    env = Environment(app)
