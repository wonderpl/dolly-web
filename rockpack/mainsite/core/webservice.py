import types
from urlparse import urlparse
from cStringIO import StringIO
from functools import wraps
from collections import namedtuple
from werkzeug.exceptions import HTTPException, Unauthorized, BadRequest, Forbidden
from flask import Blueprint, Response, request, current_app, abort, json
from rockpack.mainsite.helpers import lazy_gettext as _
from rockpack.mainsite.helpers.http import cache_for
from rockpack.mainsite.helpers.db import resize_and_upload


service_urls = namedtuple('ServiceUrl', 'url func_name func methods')


class JsonReponse(Response):
    def __init__(self, data, status=None, headers=None):
        output = request.args.get('_output')
        callback = request.args.get('_callback')
        if output == 'html':
            mimetype = 'text/html'
            dumps_args = dict(indent=True)
            head, tail = '<html><body><pre>', '</pre></body></html>'
        elif callback:
            mimetype = 'application/javascript'
            dumps_args = dict()
            head, tail = '%s(' % callback, ')'
        else:
            mimetype = 'application/json'
            dumps_args = dict(separators=(',', ':'))
            head, tail = '', ''
        body = '' if data is None else json.dumps(data, **dumps_args)
        super(JsonReponse, self).__init__(head + body + tail, status, headers, mimetype)


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


def secure_view(secure=True):
    def decorator(func):
        if not hasattr(func, '_secure'):
            func._secure = secure
        return func
    return decorator


def expose(url, methods=['GET']):
    def decorator(func):
        # attach the url details to the func so we can use it later
        if not hasattr(func, '_service_urls'):
            func._service_urls = []
        func._service_urls.append(service_urls(url=url, func_name=func.__name__, func=func, methods=methods))
        return func
    return decorator


def expose_ajax(url, methods=['GET'], secure=None, cache_age=None, cache_private=False):
    def decorator(func):
        return expose(url, methods)(secure_view(secure)(cache_for(cache_age, cache_private)(ajax(func))))
    return decorator


def ajax_create_response(instance, extra={}):
    id = extra.pop('id', instance.id)
    resource_url = extra.pop('resource_url', instance.get_resource_url(True))
    return (dict(id=id, resource_url=resource_url, **extra),
            201, [('Location', resource_url)])


def process_image(field, data=None):
    if not data:
        if request.mimetype.startswith('image/'):
            # PIL needs to seek on the data and request.stream doesn't have that
            data = StringIO(request.data)
        elif request.mimetype.startswith('multipart/form-data'):
            data = request.files['image']
        else:
            abort(400, message=_('No image data'))

    cfgkey = field.class_.__table__.columns.get(field.key).type.cfgkey

    try:
        return resize_and_upload(data, cfgkey)
    except IOError, e:
        abort(400, message=e.message or str(e))


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
        default_subdomain = app.config.get('DEFAULT_SUBDOMAIN')
        secure_subdomain = app.config.get('SECURE_SUBDOMAIN')
        api_subdomain = app.config.get('API_SUBDOMAIN')
        bp = Blueprint(self.__class__.__name__.lower(), self.__class__.__name__, url_prefix=url_prefix)
        for route in self._routes:
            # If secure is None then view should be available on all domains,
            # if True then only available on secure, if False then non-secure only
            subdomains = [api_subdomain] + ([default_subdomain] if default_subdomain else [])
            if secure_subdomain:
                secure = getattr(route.func, '_secure', None)
                if secure is True:
                    subdomains = [secure_subdomain]
                elif secure is None:
                    # Order is important here - the default should be first
                    subdomains += [secure_subdomain]
            for subdomain in subdomains:
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
            size = max(0, min(self.max_page_size, int(request.args.get('size', ''))))
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


def add_app_request_prop():
    # Try to parse user-agent for ios app version
    ua = request.user_agent
    request.rockpack_ios_version = None
    if ua.browser == 'rockpack' and ua.platform == 'ios':
        try:
            request.rockpack_ios_version = tuple(map(int, ua.version.split('.')))
        except Exception:
            pass


def setup_app_request_prop(app):
    app.before_request(add_app_request_prop)


def add_cors_headers(response):
    origin = request.args.get('_origin') or request.headers.get('Origin')
    if origin:
        hostname = urlparse(origin).hostname
        if hostname and hostname.endswith('rockpack.com'):
            response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Max-Age', current_app.config.get('CORS_MAX_AGE', 86400))
            if 'Allow' in response.headers:
                response.headers.add('Access-Control-Allow-Methods', response.headers['Allow'])
            req_headers = request.headers.get('Access-Control-Request-Headers')
            if req_headers:
                response.headers.add('Access-Control-Allow-Headers', req_headers)
    # NOTE: CloudFront strips this header so we can't really rely on it's use.
    # http://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/RequestAndResponseBehaviorCustomOrigin.html#ResponseCustomContentNegotiation
    # https://forums.aws.amazon.com/thread.jspa?messageID=388132
    response.vary.add('Origin')
    return response


def setup_cors_handling(app):
    app.after_request(add_cors_headers)
