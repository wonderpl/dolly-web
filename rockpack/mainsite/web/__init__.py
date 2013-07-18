from werkzeug.routing import MapAdapter
from flask.ext.assets import Environment
import webassets.loaders
from rockpack.mainsite import app

# Init app routes
from .views import homepage

# Init angular templates
import rockpack.mainsite.web.filters.angulartemplates


def _map_adapter_get_host(self, domain_part):
    host = self._get_host(domain_part)
    if 'DEFAULT_SUBDOMAIN' in app.config and host.startswith(app.config['DEFAULT_SUBDOMAIN']):
        return app.config['SERVER_NAME']
    else:
        return host


def setup_web(app):
    env = Environment(app)
    asset_loader = webassets.loaders.YAMLLoader('%s/assets/fullwebapp/assets.yaml' % env.directory)
    for name, bundle in asset_loader.load_bundles().items():
        env.register(name, bundle)

    # Patch werkzeug to ensure that strict_slashes redirect uses main server
    # name and not internal load-balancer name
    if 'DEFAULT_SUBDOMAIN' in app.config and not hasattr(MapAdapter, '_get_host'):
        MapAdapter._get_host = MapAdapter.get_host
        MapAdapter.get_host = _map_adapter_get_host
