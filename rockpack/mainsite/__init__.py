import os
import logging

from flask import Flask
from werkzeug.useragents import UserAgent, UserAgentParser

app = Flask(__name__)


def configure():
    app.config.from_pyfile('settings/common.py')
    app.config.from_pyfile('settings/local.py', silent=True)
    app.config.from_envvar('ROCKPACK_SETTINGS', silent=True)
    env_settings = app.config.get('ROCKPACK_ENV_SETTINGS')  # could be "prod" or "dev"
    if env_settings:
        app.config.from_pyfile('settings/%s.py' % env_settings)
configure()


if app.config.get('USE_GEVENT'):
    from gevent.monkey import patch_all
    patch_all()
    from psycogreen.gevent import patch_psycopg
    patch_psycopg()
    import grequests as requests
else:
    import requests


# for pyflakes
requests


# Patch werkzeug UserAgentParser to support rockpack app
class RockpackUserAgentParser(UserAgentParser):
    browsers = (('rockpack', 'rockpack'),) + UserAgentParser.browsers
    platforms = (('iPhone|iPad|iPod', 'ios'),) + UserAgentParser.platforms
UserAgent._parser = RockpackUserAgentParser()


try:
    from flask.ext.cache import Cache
except ImportError:
    cache = type('Cache', (object,), dict(memoize=lambda *a: lambda f: f))()
else:
    cache = Cache(app, config=app.config)


# hack to avoid django import issues via pyes
os.environ['DJANGO_SETTINGS_MODULE'] = 'none'

SERVICES = (
    'rockpack.mainsite.services.base',
    'rockpack.mainsite.services.video',
    'rockpack.mainsite.services.cover_art',
    'rockpack.mainsite.services.user',
    'rockpack.mainsite.services.search',
    'rockpack.mainsite.services.oauth',
    'rockpack.mainsite.services.share',
    'rockpack.mainsite.services.pubsubhubbub',
    'rockpack.mainsite.core.es'
)
REGISTER_SETUPS = (
    ('rockpack.mainsite.core.timing', 'setup_timing'),
    ('rockpack.mainsite.core.webservice', 'setup_abort_mapping'),
    ('rockpack.mainsite.core.webservice', 'setup_middleware'),
    ('rockpack.mainsite.admin.auth', 'setup_auth'),
    ('rockpack.mainsite.admin', 'setup_admin'),
    ('rockpack.mainsite.web', 'setup_web'),
)

WEBSERVICE_BASE = '/ws'


def run_setups():
    for import_name, name in REGISTER_SETUPS:
        setup_func = getattr(__import__(
            import_name,
            fromlist=[import_name.rsplit('.')[1]]),
            name)
        setup_func(app)


def import_services():
    from rockpack.mainsite.core.webservice import WebService
    services = []
    for s in SERVICES:
        import_name = s + '.api'
        api = __import__(import_name, fromlist=['api'])
        for a in api.__dict__.itervalues():
            if (isinstance(a, type) and issubclass(a, WebService)
                    and a.__name__ != WebService.__name__):
                services.append(a)
        try:
            __import__(s + '.commands')
        except ImportError:
            pass

    for s in services:
        endpoint = WEBSERVICE_BASE
        if s.endpoint.lstrip('/'):
            endpoint += s.endpoint
        s(app, endpoint)


def init_app():
    if not app.debug:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s: %(message)s', '%Y-%m-%dT%H:%M:%S'))
        app.logger.setLevel(app.config.get('LOG_LEVEL', logging.INFO))
        app.logger.addHandler(handler)
    if app.debug:
        try:
            from flask_debugtoolbar import DebugToolbarExtension
        except ImportError:
            pass
        else:
            DebugToolbarExtension(app)
    # Don't duplicate query log messages
    if app.config.get('SQLALCHEMY_ECHO'):
        logging.getLogger('sqlalchemy').propagate = False
    run_setups()
    import_services()
