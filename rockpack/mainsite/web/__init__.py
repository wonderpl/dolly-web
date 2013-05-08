from flask.ext.assets import Environment
import rockpack.mainsite.web.filters.angulartemplates
import webassets.loaders

# Init app routes
from .views import homepage

def setup_web(app):
    env = Environment(app)
    bundles = webassets.loaders.YAMLLoader('%s/assets/fullwebapp/assets.yaml' % env.directory).load_bundles()
    [env.register(name, bundle) for name, bundle in bundles.iteritems()]
