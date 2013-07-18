from flask.ext.assets import Environment
import rockpack.mainsite.web.filters.angulartemplates
import webassets.loaders

# Init app routes
from .views import homepage


def setup_web(app):
    env = Environment(app)
    asset_loader = webassets.loaders.YAMLLoader('%s/assets/fullwebapp/assets.yaml' % env.directory)
    for name, bundle in asset_loader.load_bundles().items():
        env.register(name, bundle)
