import types
import simplejson as json
from functools import wraps
from collections import namedtuple
from werkzeug.exceptions import HTTPException, Unauthorized, BadRequest, Forbidden
from flask import Blueprint, Response, request, current_app, abort
from rockpack.mainsite.helpers.http import cache_for


__all__ = ['WebService', 'expose']


service_urls = namedtuple('ServiceUrl', 'url func_name func methods')


class JsonReponse(Response):
    def __init__(self, data, status=None, headers=None):
        super(JsonReponse, self).__init__(
            json.dumps(data, separators=(',', ':')),
            status, headers, 'application/json')


def ajax(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            response = func(*args, **kwargs)
            if isinstance(response, Response):
                return response
            if response is None:
                response = (response, 204)
            if not isinstance(response, tuple):
                response = (response,)
            return JsonReponse(*response)
        except HTTPException, e:
            body = dict(error=getattr(e, 'error', e.name),
                        **getattr(e, 'extra', {}))
            return JsonReponse(body, e.code, e.get_headers(None))
    return wrapper


def expose(url, methods=['GET']):
    def decorator(func):
        # attach the url details to the func so we can use it later
        if not hasattr(func, '_service_urls'):
            func._service_urls = []
        func._service_urls.append(service_urls(url=url, func_name=func.__name__, func=func, methods=methods))
        return func
    return decorator


def expose_ajax(url, methods=['GET'], cache_age=None, cache_private=False):
    def decorator(func):
        return expose(url, methods)(cache_for(cache_age, cache_private)(ajax(func)))
    return decorator


class APIMeta(type):
    def __new__(cls, name, bases, dict_):
        try:
            WebService
        except NameError:
            return type.__new__(cls, name, bases, dict_)

        routes = {}
        # we need to get any service urls from expose()
        for value in dict_.values():
            if callable(value):
                urls = getattr(value, '_service_urls', ())
                for url in urls:
                    routes.setdefault(url.func.__name__, url)

        dict_['_routes'] = routes.values()
        return type.__new__(cls, name, bases, dict_)


class WebService(object):
    __metaclass__ = APIMeta

    default_page_size = 100
    max_page_size = 1000

    def __init__(self, app, url_prefix, **kwargs):
        secure_subdomain = app.config.get('SECURE_SUBDOMAIN')
        bp = Blueprint(self.__class__.__name__ + '_api', self.__class__.__name__, url_prefix=url_prefix)
        for route in self._routes:
            subdomain = getattr(route.func, '_secure', None) and secure_subdomain
            bp.add_url_rule(route.url,
                            route.func.__name__,
                            view_func=types.MethodType(route.func, self, self.__class__),
                            subdomain=subdomain,
                            methods=route.methods)

        app.register_blueprint(bp)

    def get_locale(self):
        # XXX: Perhaps we should read these from db?
        locales = current_app.config.get('ENABLED_LOCALES')
        requested = request.args.get('locale')
        return requested if requested in locales else locales[0]

    def get_page(self):
        """Check request for valid start & size args."""
        try:
            start = max(0, int(request.args.get('start', '')))
        except ValueError:
            start = 0
        try:
            size = min(self.max_page_size, int(request.args.get('size', '')))
        except ValueError:
            size = self.default_page_size
        return start, size


class Unauthorized_(Unauthorized):
    def __init__(self, description=None, error='access_denied', scheme='basic', realm='rockpack'):
        super(Unauthorized_, self).__init__(description)
        self.error = error
        self.scheme = scheme
        self.realm = realm

    def get_headers(self, environ):
        auth = '%s realm="%s"' % (self.scheme.capitalize(), self.realm)
        if self.error:
            auth += ' error="%s"' % self.error
        return super(Unauthorized_, self).get_headers(environ) +\
            [('WWW-Authenticate', auth)]


class BadRequest_(BadRequest):
    def __init__(self, description=None, error='invalid_request', **kwargs):
        super(BadRequest_, self).__init__(description)
        self.error = error
        self.extra = kwargs


class Forbidden_(Forbidden):
    def __init__(self, description=None, error='insufficient_scope'):
        super(Forbidden_, self).__init__(description)
        self.error = error


def setup_abort_mapping(app):
    # Some BadRequest excpetions are raised directly, not with abort
    # so we set json error label here
    BadRequest.error = 'invalid_request'
    abort.mapping.update({
        400: BadRequest_,
        401: Unauthorized_,
        403: Forbidden_,
    })
