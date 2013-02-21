import functools
import types
from collections import namedtuple
from flask import Blueprint, request, current_app


__all__ = ['WebService', 'expose']


service_urls = namedtuple('ServiceUrl', 'url func_name func methods')


def expose(url, methods=['GET']):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # attach the url details to the wrapper so we can use it later

        if not hasattr(wrapper, '_service_urls'):
            wrapper._service_urls = []
        wrapper._service_urls.append(service_urls(url=url, func_name=func.__name__, func=func, methods=methods))

        return wrapper

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

        bp = Blueprint(self.__class__.__name__ + '_api', self.__class__.__name__, url_prefix=url_prefix)
        for route in self._routes:
            app.logger.debug('adding route for {} on endpoint {}'.format(route.url, url_prefix))
            bp.add_url_rule(route.url,
                            route.func.__name__,
                            view_func=types.MethodType(route.func, self, self.__class__),
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
