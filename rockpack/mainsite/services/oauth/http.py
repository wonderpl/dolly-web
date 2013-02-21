import json, time
import uuid, hashlib, hmac
from functools import wraps

from flask import request, g, Response
from sqlalchemy.orm.exc import NoResultFound

from rockpack.mainsite import app
from rockpack.mainsite.services.user.models import User, LazyUser


AUTHORIZATION_ERRORS = {'invalid_request': 401,
        'invalid_token': 401,
        'unauthorized_client': 401,
        'invalid_scope': 403,
        'unsupported_response_type': 401}


class AuthToken(object):

    def __init__(self):
        self.credentials = {}
        self.refresh_token = None

    def store_refresh_token(self, user, refresh_token):
        user.refresh_token = refresh_token
        user.save()

    def get_credentials(self, user, client_id, expires_in=3600, new_refresh_token=False):
        if not self.credentials:
            self.generate_access_token(user.id, client_id, expires_in)
            if not user.refresh_token or new_refresh_token:
                self.store_refresh_token(user, self.generate_refresh_token())
            else:
                self.refresh_token = user.refresh_token
            self.credentials = self.token_dict(expires_in)
        return self.credentials

    def token_dict(self, expires_in):
        return {'access_token': self.access_token,
                'token_type': 'Bearer',
                'expires_in': expires_in,
                'refresh_token': self.refresh_token}

    def generate_refresh_token(self):
        self.refresh_token = uuid.uuid4().hex
        return self.refresh_token

    def generate_access_token(self, uid, client_id, expires_in=3600):
        expiry = time.time() + expires_in
        payload = '%s:%s:%f' % (uid, client_id, expiry)
        sig = hmac.new(app.secret_key, payload, hashlib.sha1).hexdigest()
        self.access_token = sig + payload
        return self.access_token

    @classmethod
    def verify_access_token(cls, token):
        sig, payload = token[:40], token[40:]
        if hmac.new(app.secret_key, payload, hashlib.sha1).hexdigest() == sig:
            return payload.split(':')
        return None

    def get_credentials_from_refresh_token(self, client_id, refresh_token):
        try:
            user = User.query.filter_by(refresh_token=refresh_token).one()
        except NoResultFound:
            return None
        else:
            return self.get_credentials(user, client_id)


class AccessToken(object):
    def __init__(self, token):
        a = AuthToken()
        try:
            self.uid, self.cid, self.exp = a.verify_access_token(token)
            self.exp = float(self.exp)
        except (TypeError, ValueError):
            return

    user_id = property(lambda s: getattr(s, 'uid', None))
    client_id = property(lambda s: getattr(s, 'cid', None))
    expiry = property(lambda s: getattr(s, 'exp', None))


# TODO: merge with http_response_from_data or something?
def authentication_response(error):
    return Response(json.dumps({'error': error}),
            AUTHORIZATION_ERRORS[error],
            {'WWW-Authenticate': 'Basic realm="rockpack.com" error="{}"'.format(error)},
            mimetype='application/json')


def http_response_from_data(data):
    """ Returns a Response() object based
        on data type:

        {'some': 'json style dict'}
        ('content body', 200, {'SOME': 'header'}, 'mime/type',)
        200
        FlaskResponseObject() """

    if isinstance(data, dict):
        response = Response(json.dumps(data), mimetype='application/json')
    elif isinstance(data, tuple):
        response = Response(data[0], status=data[1], headers=data[2], mimetype=data[3])
    elif isinstance(data, int):
        response = Response(status=data)
    elif isinstance(data, Response):
        response = data
    elif isinstance(data, str):
        response = Response(data)
    else:
        raise TypeError('Type {} is not supported for Response'.format(type(data)))
    return response


def validate_client_id(client_id, password):
    """ Validate whether this client_id
        exists and is allowed """

    if client_id == app.config.get('ROCKPACK_APP_CLIENT_ID'):
        return True
    return False


def verify_authorization_header(func):
    """ Checks Authorization header for Basic auth
        credentials

        Adds app_client_id to flask.g is authorized
        or 4xx response """

    @wraps(func)
    def wrapper(*args, **kwargs):
        auth = request.authorization
        error = None
        if not auth or auth.type != 'basic':
            error = 'invalid_request'
        else:
            if validate_client_id(auth.username, auth.password):
                g.app_client_id = auth.username
                r = func(*args, **kwargs)
                return http_response_from_data(r)
            error = 'unauthorized_client'
        return authentication_response(error)
    return wrapper


def parse_access_token_header(auth):
    try:
        auth_type, auth_val = auth.split(None, 1)
        auth_type = auth_type.lower()
    except (AttributeError, ValueError):
        return
    else:
        if auth_type == 'bearer':
            return AccessToken(auth_val)


def access_token_authentication(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if app.config.get('IGNORE_ACCESS_TOKEN'):
            return f(*args, **kwargs)
        auth = parse_access_token_header(request.headers.get('Authorization'))
        if auth:
            if time.time() > auth.expiry:
                return authentication_response('invalid_token')
            g.lazy_user = LazyUser(auth.user_id)
            return f(*args, **kwargs)
        return authentication_response('invalid_request')
    return wrapper
