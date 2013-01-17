__all__ = ['WebService', 'expose']

import functools
import types
from collections import namedtuple

from flask import Blueprint

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
                    routes.setdefault(url.url, url)

        dict_['_routes'] = routes.values()
        return type.__new__(cls, name, bases, dict_)

class WebService(object):
    __metaclass__ = APIMeta

    def __init__(self, app, url_prefix, **kwargs):

        bp = Blueprint(self.__class__.__name__ + '_api', self.__class__.__name__, url_prefix=url_prefix)
        for route in self._routes:
            app.logger.debug('adding route for {} on endpoint {}'.format(route.url, url_prefix))
            bp.add_url_rule(route.url,
                    route.func.__name__,
                    view_func=types.MethodType(route.func, self, self.__class__),
                    methods=route.methods)

        app.register_blueprint(bp)
