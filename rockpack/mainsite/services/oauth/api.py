import json

import wtforms
from wtforms import validators
from flask import request, Response, g


from rockpack.mainsite.core.webservice import WebService, expose
from rockpack.mainsite.services.video.models import Channel
from rockpack.mainsite.services.user.models import User
from . import models
from .http import verify_authorization_header, authentication_response, AuthToken
from .exceptions import InvalidExternalSystem


def user_authenticated(username, password):
    user = User.get_from_username(username)
    if user and user.check_password(password):
        return user
    return False


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

    @expose('/external/', methods=('POST',))
    @verify_authorization_header
    def exeternal(self):
        if request.form.get('grant_type') == 'token':
            user = models.ExternalToken.user_from_token()
            if user:
                a = AuthToken()
                credentials = a.get_credentials(user,
                        g.app_client_id,
                        new_refresh_token=True)
                return credentials

        return 400


class RockRegistrationForm(wtforms.Form):
    username = wtforms.TextField(validators=[validators.Required()])
    password = wtforms.PasswordField(validators=[validators.Required()])
    first_name = wtforms.TextField(validators=[validators.Required()])
    last_name = wtforms.TextField(validators=[validators.Required()])
    email = wtforms.TextField(validators=[validators.Required()])


class ExternalRegistrationForm(RockRegistrationForm):
    external_system = wtforms.TextField(validators=[validators.Required()])
    external_token = wtforms.TextField(validators=[validators.Required()])

    password = wtforms.PasswordField()

    def validate_external_system(form, value):
        if value in models.EXTERNAL_SYSTEM_NAMES:
            return validators.ValidationError('external system invalid')


DEFAULT_USER_CHANNEL = ('favourites', 'starred videos on rockpack by me')


def new_user_setup(form):
    """ Creates a new user and sets up
        and related assets, like default channels """

    user = User(username=form.username.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            is_active=True)
    user = user.save()
    user.set_password(form.password.data)

    channel = Channel(title=DEFAULT_USER_CHANNEL[0],
            description=DEFAULT_USER_CHANNEL[1],
            cover='',
            owner=user.id)
    channel.save()
    return user


class Registration(WebService):
    endpoint = '/register'

    @expose('/', methods=('POST',))
    @verify_authorization_header
    def register(self):
        form = RockRegistrationForm(request.form)
        if request.form.get('register', '0') == '1' and form.validate():
            user = new_user_setup(form)

            a = AuthToken()
            credentials = a.get_credentials(user,
                    g.app_client_id,
                    new_refresh_token=True)
            return credentials

        return 400

    @expose('/external/', methods=('POST',))
    @verify_authorization_header
    def external(self):
        form = ExternalRegistrationForm(request.form)
        if request.form.get('register', '0') == '1' and form.validate():
            user = new_user_setup(form)

            try:
                models.ExternalToken.update_token(user,
                        form.external_system.data, form.external_token.data)
            except InvalidExternalSystem:
                pass
            else:
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
