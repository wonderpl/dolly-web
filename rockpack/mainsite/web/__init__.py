import os
from werkzeug.routing import MapAdapter
from flask.ext.assets import Environment
import webassets.loaders
from jinja2 import Markup
from rockpack.mainsite import app

# Init app routes
from .views import homepage     # NOQA

# Init angular templates
import rockpack.mainsite.web.filters.angulartemplates   # NOQA


def _map_adapter_get_host(self, domain_part):
    host = self._get_host(domain_part)
    if 'DEFAULT_SUBDOMAIN' in app.config and host.startswith(app.config['DEFAULT_SUBDOMAIN']):
        return app.config['SERVER_NAME']
    else:
        return host


def _include_static_inline(path):
    i = path.find('/static/')
    if i >= 0:
        path = path[i + 8:]
    path = os.path.join(app.static_folder, path)
    with open(path) as f:
        return Markup(f.read())


def setup_web(app):
    env = Environment(app)
    asset_loader = webassets.loaders.YAMLLoader('%s/assets/fullwebapp/assets.yaml' % env.directory)
    for name, bundle in asset_loader.load_bundles().items():
        env.register(name, bundle)

    # Use own url_for to force absolute urls with correct domains
    from rockpack.mainsite.helpers.urls import url_for
    app.jinja_env.globals.update(url_for=url_for)

    # Patch werkzeug to ensure that strict_slashes redirect uses main server
    # name and not internal load-balancer name
    if 'DEFAULT_SUBDOMAIN' in app.config and not hasattr(MapAdapter, '_get_host'):
        MapAdapter._get_host = MapAdapter.get_host
        MapAdapter.get_host = _map_adapter_get_host

    app.jinja_env.globals.update(include_static_inline=_include_static_inline)

    static_path = app.jinja_loader.searchpath[0].replace('/templates', '/static')
    app.jinja_loader.searchpath.append(static_path)

    if app.config.get('DOLLY'):
        dolly_path = app.jinja_loader.searchpath[0] + '/dolly/'
        app.jinja_loader.searchpath.insert(0, dolly_path)
