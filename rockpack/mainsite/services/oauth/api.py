from cStringIO import StringIO
from flask import request
from flask import abort
from flask.ext import wtf
import requests
import facebook
from rockpack.mainsite import app
from rockpack.mainsite.core.oauth.decorators import check_client_authorization
from rockpack.mainsite.core.webservice import WebService
from rockpack.mainsite.core.webservice import expose_ajax
from rockpack.mainsite.services.user.models import User
from rockpack.mainsite.services.video.models import Locale
from . import models


def user_authenticated(username, password):
    user = User.get_from_username(username)
    if user and user.check_password(password):
        return user
    return False


if app.config.get('TEST_EXTERNAL_SYSTEM'):
    @app.route('/test/fb/login/')
    def test_fb():
        from flask import render_template
        return render_template('fb_test.html')


class Login(WebService):

    endpoint = '/login'

    @expose_ajax('/', methods=['POST'])
    @check_client_authorization
    def login(self):
        if not request.form['grant_type'] == 'password':
            abort(400)
        user = user_authenticated(request.form['username'], request.form['password'])
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
            user = User.create_from_external_system(
                username=eu.username,
                first_name=eu.first_name,
                last_name=eu.last_name,
                locale=eu.locale,
                avatar=eu.avatar,
                external_system=form.external_system.data,
                external_token=form.external_token.data,
                external_uid=eu.id)
        else:
            # Update the token record
            models.ExternalToken.update_token(
                user=user,
                external_system=form.external_system.data,
                token=form.external_token.data,
                external_uid=eu.id)

        return user.get_credentials()


class RockRegistrationForm(wtf.Form):
    username = wtf.TextField(validators=[wtf.Required()])
    password = wtf.PasswordField(validators=[wtf.Required()])
    first_name = wtf.TextField()
    last_name = wtf.TextField()
    locale = wtf.TextField(validators=[wtf.Required()])
    email = wtf.TextField(validators=[wtf.Required(), wtf.Email()])

    def validate_username(form, field):
        if User.query.filter_by(username=field.data).count():
            raise wtf.ValidationError('"%s" already taken' % field.data)

        if field.data != User.sanitise_username(field.data):
            raise wtf.ValidationError('Username can only contain alphanumerics')

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
    valid_token = False

    def __init__(self, system, token):
        self._user_data = {}
        self.token = token

        self._user_data = self._get_external_data(system, token)
        if self._user_data:
            self.valid_token = True

    def _get_external_data(self, system, token):
        try:
            graph = facebook.GraphAPI(token)
        except facebook.GraphAPIError:
            return {}
        return graph.get_object('me')

    id = property(lambda x: x._user_data.get('id'))
    username = property(lambda x: x._user_data.get('username'))
    first_name = property(lambda x: x._user_data.get('first_name', ''))
    last_name = property(lambda x: x._user_data.get('last_name', ''))
    display_name = property(lambda x: x._user_data.get('name', ''))

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


class Registration(WebService):
    endpoint = '/register'

    @expose_ajax('/', methods=['POST'])
    @check_client_authorization
    def register(self):
        form = RockRegistrationForm(request.form, csrf_enabled=False)
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


class Token(WebService):
    endpoint = '/token'

    @expose_ajax('/', methods=['POST'])
    @check_client_authorization
    def token(self):
        refresh_token = request.form['refresh_token']
        if request.form['grant_type'] != 'refresh_token' or not refresh_token:
            abort(400)
        user = User.query.filter_by(refresh_token=refresh_token).first()
        if not user:
            abort(400, error='invalid_grant')
        return user.get_credentials()
