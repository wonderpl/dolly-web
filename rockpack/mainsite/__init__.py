from flask import Flask

#from rockpack.services.video import api

app = Flask(__name__)

app.config.from_pyfile('settings/common.py')
app.config.from_pyfile('settings/local.py', silent=True)
app.config.from_envvar('ROCKPACK_SETTINGS', silent=True)


SERVICES = (
    'rockpack.mainsite.services.video',
    'rockpack.mainsite.services.cover_art',
    'rockpack.mainsite.services.user',
    'rockpack.mainsite.services.search',
    'rockpack.mainsite.services.oauth',
    'rockpack.mainsite.services.pubsubhubbub',
)
REGISTER_SETUPS = (
    ('rockpack.mainsite.admin.auth', 'setup_auth'),
    ('rockpack.mainsite.admin', 'setup_admin'),
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
    from rockpack.mainsite.core.webservice import WebService  # TODO: move this, obviously
    services = []
    for s in SERVICES:
        import_name = s + '.api'
        api = __import__(import_name, fromlist=['api'])
        for a in api.__dict__.itervalues():
            if (isinstance(a, type) and issubclass(a, WebService)
                    and a.__name__ != WebService.__name__):
                services.append(a)

    for s in services:
        app.logger.debug('loading service: {}'.format(s.__name__))
        endpoint = WEBSERVICE_BASE
        if s.endpoint.lstrip('/'):
            endpoint += s.endpoint
        s(app, endpoint)


def init_app():
    run_setups()
    import_services()
