import uuid
import hashlib
import hmac
import time
import json
from functools import wraps
from flask import request, Response, g
from wtforms import validators
import wtforms

from sqlalchemy.orm.exc import NoResultFound

from rockpack.mainsite import app
from rockpack.mainsite.core.webservice import WebService, expose
from rockpack.mainsite.services.user.models import User


def validate_client_id(client_id, password):
    """ Validate whether this client_id
        exists and is allowed """

    if client_id == app.config.get('ROCKPACK_APP_CLIENT_ID'):
        return True
    return False


AUTHORIZATION_ERRORS = {'invalid_request': 401,
        'invalid_token': 401,
        'unauthorized_client': 401,
        'invalid_scope': 403,
        'unsupported_response_type': 401}


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


def user_authenticated(username, password):
    user = User.get_from_username(username)
    if user and user.check_password(password):
        return user
    return False


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

    def get_credentials_from_refresh_token(self, client_id, refresh_token):
        try:
            user = User.query.filter_by(refresh_token=refresh_token).one()
        except NoResultFound:
            return None
        else:
            return self.get_credentials(user, client_id)


class Login(WebService):

    endpoint = '/login'

    @expose('/', methods=('POST',))
    @verify_authorization_header
    def login(self):
        if request.form.get('grant_type') == 'password':
            user = user_authenticated(request.form.get('username'), request.form.get('password'))
            if user:
                a = AuthToken()
                credentials = a.get_credentials(user,
                        g.app_client_id,
                        new_refresh_token=True)
                return credentials

        return Response(json.dumps({'error': 'access_denied'}), 401)


class RockRegistrationForm(wtforms.Form):
    username = wtforms.TextField(validators=[validators.Required()])
    password = wtforms.PasswordField(validators=[validators.Required()])
    first_name = wtforms.TextField(validators=[validators.Required()])
    last_name = wtforms.TextField(validators=[validators.Required()])
    email = wtforms.TextField(validators=[validators.Required()])


class Registration(WebService):
    endpoint = '/register'

    @expose('/', methods=('POST',))
    @verify_authorization_header
    def register(self):
        form = RockRegistrationForm(request.form)
        if request.form.get('register', '0') == '1' and form.validate():
            user = User(username=form.username.data,
                    first_name=form.first_name.data,
                    last_name=form.last_name.data,
                    email=form.email.data,
                    is_active=True,
                    avatar=request.files.get('avatar'))
            user = user.save()
            user.set_password(form.password.data)

            a = AuthToken()
            credentials = a.get_credentials(user,
                    g.app_client_id,
                    new_refresh_token=True)
            return credentials

        return 400


class Token(WebService):
    endpoint = '/token'

    @expose('/', methods=('POST',))
    @verify_authorization_header
    def token(self):
        refresh_token = request.form.get('refresh_token')
        if request.form.get('grant_type') == 'refresh_token' and refresh_token:
            a = AuthToken()
            credentials = a.get_credentials_from_refresh_token(g.app_client_id, refresh_token)
            if credentials:
                return credentials

        return authentication_response('invalid_request')
