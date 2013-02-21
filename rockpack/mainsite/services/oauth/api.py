import json
import uuid
from flask import request, Response
from flask.ext import wtf
from rockpack.mainsite.core.webservice import WebService, expose
from rockpack.mainsite.services.video.models import Channel
from rockpack.mainsite.services.user.models import User
from . import models
from .http import verify_authorization_header, authentication_response
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
                return user.get_credentials()
        return Response(json.dumps({'error': 'access_denied'}), 401)

    @expose('/external/', methods=('POST',))
    @verify_authorization_header
    def exeternal(self):
        if request.form.get('grant_type') == 'token':
            user = models.ExternalToken.user_from_token()
            if user:
                return user.get_credentials()
        return 400


class RockRegistrationForm(wtf.Form):
    username = wtf.TextField(validators=[wtf.Required()])
    password = wtf.PasswordField(validators=[wtf.Required()])
    first_name = wtf.TextField()
    last_name = wtf.TextField()
    email = wtf.TextField(validators=[wtf.Required(), wtf.Email()])

    def validate_username(form, field):
        if User.query.filter_by(username=field.data).count():
            raise wtf.ValidationError('"%s" already taken' % field.data)


class ExternalRegistrationForm(RockRegistrationForm):
    external_system = wtf.TextField(validators=[wtf.Required()])
    external_token = wtf.TextField(validators=[wtf.Required()])

    password = wtf.PasswordField()

    def validate_external_system(form, value):
        if value in models.EXTERNAL_SYSTEM_NAMES:
            return wtf.ValidationError('external system invalid')


DEFAULT_USER_CHANNEL = ('favourites', 'starred videos on rockpack by me')


def new_user_setup(form):
    """ Creates a new user and sets up
        and related assets, like default channels """

    user = User(
        username=form.username.data,
        first_name=form.first_name.data,
        last_name=form.last_name.data,
        email=form.email.data,
        password_hash='',
        refresh_token=uuid.uuid4().hex,
        avatar='',
        is_active=True)
    user = user.save()
    user.set_password(form.password.data)

    channel = Channel(
        title=DEFAULT_USER_CHANNEL[0],
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
        form = RockRegistrationForm(request.form, csrf_enabled=False)
        if form.validate():
            user = new_user_setup(form)
            return user.get_credentials()
        # XXX: Need to return to the client some message about invalid data
        return 400

    @expose('/external/', methods=('POST',))
    @verify_authorization_header
    def external(self):
        form = ExternalRegistrationForm(request.form, csrf_enabled=False)
        if form.validate():
            user = new_user_setup(form)
            try:
                models.ExternalToken.update_token(
                    user, form.external_system.data, form.external_token.data)
            except InvalidExternalSystem:
                pass
            else:
                return user.get_credentials()
        return 400


class Token(WebService):
    endpoint = '/token'

    @expose('/', methods=('POST',))
    @verify_authorization_header
    def token(self):
        refresh_token = request.form.get('refresh_token')
        if request.form.get('grant_type') == 'refresh_token' and refresh_token:
            user = User.query.filter_by(refresh_token=refresh_token).first()
            if user:
                return user.get_credentials()
        return authentication_response('invalid_request')
