from functools import wraps


def add_response_headers(headers={}):
    """This decorator adds the headers passed in to the response"""
    def decorator(f):
        @wraps(f)
        def func(*args, **kwargs):
            resp = f(*args, **kwargs)
            h = resp.headers
            for header, value in headers.items():
                h[header] = value
            return resp
        return func
    return decorator


def cache_for(seconds=None):
    def decorator(f):
        if seconds is not None:
            return add_response_headers(
                {'Cache-Control': 'max-age={}'.format(seconds)})(f)
    return decorator
