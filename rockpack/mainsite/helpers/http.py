from cStringIO import StringIO
from werkzeug import FileStorage
from functools import wraps
from flask import request
from rockpack.mainsite import requests


def add_response_headers(headers={}, cache_max_age=None, cache_private=False):
    """This decorator adds the headers passed in to the response"""
    def decorator(f):
        @wraps(f)
        def func(*args, **kwargs):
            resp = f(*args, **kwargs)
            h = resp.headers
            for header, value in headers.items():
                h[header] = value
            if '_nc' in request.args:
                resp.cache_control.no_cache = True
            else:
                if cache_private:
                    resp.cache_control.private = True
                if cache_max_age:
                    if not resp.cache_control.private:
                        resp.cache_control.public = True
                    resp.cache_control.max_age = cache_max_age
                    # Always add ETag to cached responses
                    resp.add_etag()
                    resp.make_conditional(request)
            return resp
        return func
    return decorator


def cache_for(seconds=None, private=False):
    return add_response_headers(cache_max_age=seconds, cache_private=private)


def get_external_resource(url):
    """Get the specified http resource and return a FileStorage-wrapped buffer."""
    response = requests.get(url)
    response.raise_for_status()
    return FileStorage(StringIO(response.content), response.url)
