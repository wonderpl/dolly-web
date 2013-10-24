from urllib import urlencode
from functools import wraps
from flask import request, Response, redirect, render_template, json
from rockpack.mainsite import app
from rockpack.mainsite.helpers.http import cache_for
from rockpack.mainsite.helpers.urls import url_for


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
        subdomains = [(None, '')]
        if app.config.get('DEFAULT_SUBDOMAIN'):
            subdomains.append((app.config.get('DEFAULT_SUBDOMAIN'), '_default'))
        if secure and app.config.get('SECURE_SUBDOMAIN'):
            subdomains = [(app.config.get('SECURE_SUBDOMAIN'), '')]
        for subdomain, suffix in subdomains:
            name = func.func_name + suffix
            app.add_url_rule(url, name, cache_for(cache_age, cache_private)(render(template)(func)),
                             methods=methods, subdomain=subdomain)
        return func
    return decorator


def iframe_proxy_redirect():
    """Take AJAX result and pass it to iframe_proxy via a 302 redirect."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            response = func(*args, **kwargs)
            proxy_url = url_for('iframe_proxy')
            params = dict(result=json.dumps(response))
            callback = request.args.get('_callback') or request.form.get('_callback')
            if callback:
                params['_callback'] = callback
            return redirect(proxy_url + '?' + urlencode(params))
        return wrapper
    return decorator
