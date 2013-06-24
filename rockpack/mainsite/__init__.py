import os
import logging
from flask import Flask

app = Flask(__name__)


def configure():
    app.config.from_pyfile('settings/common.py')
    app.config.from_pyfile('settings/local.py', silent=True)
    app.config.from_envvar('ROCKPACK_SETTINGS', silent=True)
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
)
REGISTER_SETUPS = (
    ('rockpack.mainsite.core.timing', 'setup_timing'),
    ('rockpack.mainsite.core.webservice', 'setup_cors_handling'),
    ('rockpack.mainsite.core.webservice', 'setup_abort_mapping'),
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
        app.logger.addHandler(handler)
    if app.debug:
        try:
            from flask_debugtoolbar import DebugToolbarExtension
        except ImportError:
            pass
        else:
            DebugToolbarExtension(app)
    run_setups()
    import_services()
