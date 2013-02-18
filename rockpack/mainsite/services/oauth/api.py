import uuid
import base64
import hashlib
import hmac
import time
from flask import request, Response, jsonify
import wtforms
from wtforms import validators

from rockpack.mainsite import app
from rockpack.mainsite.core.webservice import WebService, expose
from rockpack.mainsite.auth.models import User


def validate_client_id(client_id, password):
    """ Validate whether this client_id
        exists and is allowed """

    raise NotImplementedError('client id check not implemented')
    if client_id in '':
        return True
    return False


def verify_authorization_header():
    """ Checks Authorization header for Basic auth
        credentials

        Returns a client_id or `False`"""

    try:
        _type, token = request.headers.get('Authorization', '').split()
        client_id, password = base64.decodestring(token).split(':')
    except ValueError:
        pass
    else:
        if _type == 'Basic' and validate_client_id(client_id, password):
            return client_id
    return False


def user_authenticated():
    username = request.form.get('username', '')
    password = request.form.get('password', '')

    user = User.get_from_username(username)
    if user and user.check_password_hash(password):
        return True
    return False


class AuthToken(object):

    def __init__(self):
        self.credentials = {}

    def store_refresh_token(self):
        return NotImplementedError('store_refresh_token must be defined')

    def get_credentials(self, uid, client_id, expires_in=3600):
        if not self.credentials:
            self.generate_access_token(uid, client_id, expires_in)
            self.generate_refresh_token()
            self.store_refresh_token()
            self.credentials = self.token_dict(expires_in)
        return self.credentials

    def token_dict(self, expires_in):
        return {'access_token': self.access_token,
                'token_type': 'Bearer',
                'expires_in': expires_in,
                'refresh_token': self.refresh_token}

    def generate_refresh_token(self):
        self.refresh_token = uuid.uuid4().hex

    def generate_access_token(self, uid, client_id, expires_in):
        expiry = time.time() + expires_in
        payload = '%s:%s:%f' % (uid, client_id, expiry)
        sig = hmac.new(app.secret_key, payload, hashlib.sha1).hexdigest()
        self.access_token = sig + payload


class Login(WebService):

    endpoint = '/login'

    @expose('/', methods=('POST',))
    def login(self):
        response = Response(content_type='application/json', status=400)

        client_id = verify_authorization_header()
        if client_id and request.form.get('grant_type', '') == 'password'\
                and user_authenticated(request.form.get('username'),
                        request.form.get('password')):
            a = AuthToken()
            credentials = a.get_credentials(request.form.get('username'), client_id, 3600)
            return jsonify(credentials)

        return response


class RockRegistrationForm(wtforms.Form):
    username = wtforms.TextField(validators=[validators.Required()])
    password = wtforms.PasswordField(validators=[validators.Required()])
    first_name = wtforms.TextField(validators=[validators.Required()])
    last_name = wtforms.TextField(validators=[validators.Required()])
    email = wtforms.TextField(validators=[validators.Required()])


class Registration(WebService):
    endpoint = '/register'

    @expose('/', methods=('POST',))
    def register(self):
        client_id = verify_authorization_header()
        form = RockRegistrationForm(request.form)
        if request.form.get('grant_type') == 'password' and\
                request.form.get('register', '0') == '1' and form.validate():
            user = User(username=form.username.data,
                    first_name=form.first_name.data,
                    last_name=form.last_name.data,
                    email=form.email.data,
                    is_active=True,
                    avatar=request.files.get('avatar'))
            user.save()
            user.set_password(form.password.data)

            return Response(status=201)

        return Response(status=400)


class Token(WebService):
    endpoint = '/token'
