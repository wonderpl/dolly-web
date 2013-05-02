from functools import wraps
from flask import Response, render_template
from rockpack.mainsite import app
from rockpack.mainsite.helpers.http import cache_for


def render(template=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            response = func(*args, **kwargs)
            if isinstance(response, Response):
                return response
            if not isinstance(response, tuple):
                response = (response,)
            if template:
                response = (render_template(template, **(response[0] or {})),) + response[1:]
            return Response(*response)
        return wrapper
    return decorator


def expose_web(url, template=None, methods=['GET'], secure=None, cache_age=None, cache_private=False):
    def decorator(func):
        subdomains = [None]
        if app.config.get('DEFAULT_SUBDOMAIN'):
            subdomains.append(app.config.get('DEFAULT_SUBDOMAIN'))
        if secure and app.config.get('SECURE_SUBDOMAIN'):
            subdomains = [app.config.get('SECURE_SUBDOMAIN')]
        for subdomain in subdomains:
            app.add_url_rule(url, None, cache_for(cache_age, cache_private)(render(template)(func)),
                             methods=methods, subdomain=subdomain)
        return func
    return decorator
