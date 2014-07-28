# Hack to prevent import lock issue
# http://code.google.com/p/modwsgi/issues/detail?id=177
import _strptime    # NOQA

import logging
from werkzeug.contrib.fixers import ProxyFix
from flask import request
from rockpack.mainsite import app, init_app

init_app()

app.wsgi_app = ProxyFix(app.wsgi_app)

if 'SENTRY_DSN' in app.config:
    from raven.contrib.flask import Sentry
    Sentry(app, logging=app.config.get('SENTRY_ENABLE_LOGGING'), level=logging.WARN)

if 'SECURE_SUBDOMAIN' in app.config:
    def check_if_secure():
        # Throw 404 if secure view is requested without https
        if (request.url_rule and
                request.url_rule.subdomain == app.config['SECURE_SUBDOMAIN'] and
                not request.is_secure):
            return 'Insecurities make the world go round', 404
    app.before_request(check_if_secure)

if 'AUTH_HEADER_SANITY_CHECK' in app.config:
    def check_auth_header():
        if not request.is_secure and 'Authorization' in request.headers:
            return 'A small leak will sink a great ship', 412
    app.before_request(check_auth_header)

if 'ENABLE_RESPONSE_TESTS' in app.config:
    def check_test_response_header():
        response_code = request.headers.get('X-Rockpack-Test-Response')
        if response_code:
            return response_code, int(response_code)
    app.before_request(check_test_response_header)

application = app
