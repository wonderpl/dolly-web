from functools import wraps
from flask import request, abort, g
from rockpack.mainsite import app
from rockpack.mainsite.core.token import parse_access_token, ExpiredTokenError
from rockpack.mainsite.services.user.models import User


def check_client_authorization(f):
    """Check Authorization header for valid client id"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.type != 'basic':
            abort(401, error='invalid_request')
        if auth.username != app.config['ROCKPACK_APP_CLIENT_ID']:
            abort(401, error='unauthorized_client')
        g.app_client_id = auth.username
        return f(*args, **kwargs)
    # All views decorated with this are secure by default
    wrapper._secure = True
    return wrapper


class RequestUser(object):
    def __init__(self, userid, clientid=None):
        self.userid = userid
        self.clientid = clientid

    def __nonzero__(self):
        return bool(self.userid)

    @property
    def user(self):
        if self.userid:
            return User.query.get(self.userid)


def check_authorization(abort_on_fail=True, self_auth=False):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            g.authorized = RequestUser(None)
            auth_header = request.headers.get('Authorization', '')
            error = 'invalid_token'
            try:
                auth_type, auth_val = auth_header.split(None, 1)
            except ValueError:
                pass
            else:
                if auth_type.lower() == 'bearer':
                    try:
                        userid, clientid = parse_access_token(auth_val)
                    except ExpiredTokenError:
                        error = 'expired_token'
                    except TypeError:
                        pass
                    else:
                        g.authorized = RequestUser(userid, clientid)
                        if self_auth and not kwargs['userid'] == userid:
                            abort(403)
            if not g.authorized and abort_on_fail:
                abort(401, scheme='bearer', error=error)
            return f(*args, **kwargs)
        # require secure unless abort_on_fail is False
        wrapper._secure = None if abort_on_fail is False else True
        return wrapper
    return decorator
