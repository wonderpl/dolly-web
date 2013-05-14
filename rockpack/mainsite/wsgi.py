from werkzeug.contrib.fixers import ProxyFix
from flask import request
from rockpack.mainsite import app, init_app

init_app()

app.wsgi_app = ProxyFix(app.wsgi_app)

if 'SENTRY_DSN' in app.config:
    from raven.contrib.flask import Sentry
    Sentry(app, logging=app.config.get('SENTRY_ENABLE_LOGGING'))

if 'SECURE_SUBDOMAIN' in app.config:
    def check_if_secure():
        # Throw 404 if secure view is requested without https
        if (request.url_rule and
                request.url_rule.subdomain == app.config['SECURE_SUBDOMAIN'] and
                not request.is_secure):
            return 'Insecurities make the world go round', 404
    app.before_request(check_if_secure)

application = app
