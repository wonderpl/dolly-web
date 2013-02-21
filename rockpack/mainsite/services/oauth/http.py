import json
from functools import wraps
from flask import request, g, Response
from rockpack.mainsite import app
from rockpack.mainsite.core.token import parse_access_token
from rockpack.mainsite.services.user.models import User


AUTHORIZATION_ERRORS = {
    'invalid_request': 401,
    'invalid_token': 401,
    'unauthorized_client': 401,
    'invalid_scope': 403,
    'unsupported_response_type': 401}


# TODO: merge with http_response_from_data or something?
def authentication_response(error):
    return Response(
        json.dumps({'error': error}),
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


def parse_access_token_header(auth_header):
    try:
        auth_type, auth_val = auth_header.split(None, 1)
    except (AttributeError, ValueError):
        return
    else:
        if auth_type.lower() == 'bearer':
            return parse_access_token(auth_val)


class RequestUser(object):
    def __init__(self, userid, clientid):
        self.userid = userid
        self.clientid = clientid

    def __nonzero__(self):
        return self.userid

    @property
    def user(self):
        if self.userid:
            return User.query.get(self.userid)


def access_token_authentication(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if app.config.get('IGNORE_ACCESS_TOKEN'):
            return f(*args, **kwargs)
        try:
            userid, clientid = parse_access_token_header(request.headers.get('Authorization'))
        except TypeError:
            pass
        else:
            g.authorized = RequestUser(userid, clientid)
            return f(*args, **kwargs)
        return authentication_response('invalid_request')
    return wrapper
