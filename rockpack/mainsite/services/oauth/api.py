from datetime import datetime, timedelta
from cStringIO import StringIO
from flask import request, abort
from flask.ext import wtf
import requests
from rockpack.mainsite import app
from rockpack.mainsite.core.oauth.decorators import check_client_authorization
from rockpack.mainsite.core.webservice import WebService, expose_ajax
from rockpack.mainsite.services.user.models import User, username_exists
from rockpack.mainsite.services.video.models import Locale
from . import facebook, models


if app.config.get('TEST_EXTERNAL_SYSTEM'):
    @app.route('/test/fb/login/', subdomain=app.config.get('SECURE_SUBDOMAIN'))
    def test_fb():
        from flask import render_template
        from test.test_helpers import get_client_auth_header
        return render_template('fb_test.html',
                               client_auth_headers=[get_client_auth_header()])


class LoginWS(WebService):

    endpoint = '/login'

    @expose_ajax('/', methods=['POST'])
    @check_client_authorization
    def login(self):
        if not request.form['grant_type'] == 'password':
            abort(400, error='unsupported_grant_type')
        user = User.get_from_credentials(request.form['username'], request.form['password'])
        if not user:
            abort(400, error='invalid_grant')
        return user.get_credentials()

    @expose_ajax('/external/', methods=['POST'])
    @check_client_authorization
    def exeternal(self):
        form = ExternalRegistrationForm(request.form, csrf_enabled=False)
        if not form.validate():
            abort(400, form_errors=form.errors)

        eu = ExternalUser(form.external_system.data, form.external_token.data)
        if not eu.valid_token:
            abort(400, error='unauthorized_client')

        user = models.ExternalToken.user_from_uid(
            request.form.get('external_system'),
            eu.id)

        if not user:
            # New user
            user = User.create_from_external_system(eu)

        # Update the token record if needed
        models.ExternalToken.update_token(user, eu)

        return user.get_credentials()


class RockRegistrationForm(wtf.Form):
    username = wtf.TextField(validators=[wtf.Required()])
    password = wtf.PasswordField(validators=[wtf.Required()])
    first_name = wtf.TextField()
    last_name = wtf.TextField()
    locale = wtf.TextField(validators=[wtf.Required()])
    email = wtf.TextField(validators=[wtf.Required(), wtf.Email()])

    def validate_username(form, field):
        if field.data != User.sanitise_username(field.data):
            raise wtf.ValidationError('Username can only contain alphanumerics')
        exists = username_exists(field.data)
        if exists == 'reserved':
            raise wtf.ValidationError('"%s" is reserved' % field.data)
        elif exists:
            raise wtf.ValidationError('"%s" already taken' % field.data)

    def validate_email(form, field):
        if User.query.filter_by(email=field.data).count():
            raise wtf.ValidationError('Email address already registered')


class ExternalRegistrationForm(wtf.Form):
    external_system = wtf.TextField(validators=[wtf.Required()])
    external_token = wtf.TextField(validators=[wtf.Required()])

    def validate_external_system(form, value):
        if value.data not in models.EXTERNAL_SYSTEM_NAMES:
            raise wtf.ValidationError('external system invalid')


# TODO: currently only Facebook - change
class ExternalUser:

    def __init__(self, system, token, expires_in=None):
        self._user_data = {}
        self._valid_token = False
        self._token = token
        self._system = system

        if expires_in:
            self._expires = datetime.utcnow() + timedelta(seconds=expires_in)
        else:
            self._expires = None

        self._user_data = self._get_external_data()
        if self._user_data:
            self._valid_token = True

    def _get_external_data(self):
        try:
            graph = facebook.GraphAPI(self._token)
        except facebook.GraphAPIError:
            return {}
        return graph.get_object('me')

    def get_new_token(self):
        # abstract this out to not be fb specific
        token, expires = facebook.renew_token(
            self._token,
            app.config['FACEBOOK_APP_ID'],
            app.config['FACEBOOK_APP_SECRET'])
        return self.__class__('facebook', token, expires)

    id = property(lambda x: x._user_data.get('id'))
    username = property(lambda x: x._user_data.get('username'))
    first_name = property(lambda x: x._user_data.get('first_name', ''))
    last_name = property(lambda x: x._user_data.get('last_name', ''))
    display_name = property(lambda x: x._user_data.get('name', ''))
    valid_token = property(lambda x: x._valid_token)
    token = property(lambda x: x._token)
    system = property(lambda x: x._system)
    expires = property(lambda x: x._expires)

    @property
    def email(self):
        if 'email' in self._user_data:
            return self._user_data['email']
        elif 'username' in self._user_data:
            return '%s@facebook.com' % self._user_data['username']
        else:
            return ''

    @property
    def locale(self):
        l = self._user_data.get('locale', '').lower().replace('_', '-')
        if not Locale.query.get(l):
            return ''
        return l

    @property
    def avatar(self):
        r = requests.get('http://graph.facebook.com/{}/picture/?type=large'.format(self.id))
        if r.status_code == 200 and r.headers.get('content-type', '').startswith('image/'):
            return StringIO(r.content)
        return ''


class RegistrationWS(WebService):
    endpoint = '/register'

    @expose_ajax('/', methods=['POST'])
    @check_client_authorization
    def register(self):
        form = RockRegistrationForm(csrf_enabled=False)
        if not form.validate():
            abort(400, form_errors=form.errors)
        user = User.create_with_channel(
            username=form.username.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            password=form.password.data,
            locale=form.locale.data)
        return user.get_credentials()


class TokenWS(WebService):
    endpoint = '/token'

    @expose_ajax('/', methods=['POST'])
    @check_client_authorization
    def token(self):
        refresh_token = request.form['refresh_token']
        if request.form['grant_type'] != 'refresh_token' or not refresh_token:
            abort(400, error='unsupported_grant_type')
        user = User.query.filter_by(refresh_token=refresh_token).first()
        if not user:
            abort(400, error='invalid_grant')
        return user.get_credentials()
