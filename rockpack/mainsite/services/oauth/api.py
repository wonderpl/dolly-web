import uuid
from flask import request, abort
from flask.ext import wtf
from rockpack.mainsite import app
from rockpack.mainsite.core.oauth.decorators import check_client_authorization
from rockpack.mainsite.core.webservice import WebService, expose_ajax
from rockpack.mainsite.services.video.models import Channel
from rockpack.mainsite.services.user.models import User
from . import models
from .exceptions import InvalidExternalSystem


def user_authenticated(username, password):
    user = User.get_from_username(username)
    if user and user.check_password(password):
        return user
    return False


class LoginWS(WebService):

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
        if not request.form['grant_type'] == 'token':
            abort(400)
        user = models.ExternalToken.user_from_token()
        if not user:
            abort(400, error='invalid_grant')
        return user.get_credentials()


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

    title, description, cover = app.config['FAVOURITE_CHANNEL']
    channel = Channel(
        title=title,
        description=description,
        cover=cover,
        owner=user.id)
    channel.save()

    return user


class RegistrationWS(WebService):
    endpoint = '/register'

    @expose_ajax('/', methods=['POST'])
    @check_client_authorization
    def register(self):
        form = RockRegistrationForm(request.form, csrf_enabled=False)
        if not form.validate():
            abort(400, form_errors=form.errors)
        user = new_user_setup(form)
        return user.get_credentials()

    @expose_ajax('/external/', methods=['POST'])
    @check_client_authorization
    def external(self):
        form = ExternalRegistrationForm(request.form, csrf_enabled=False)
        if not form.validate():
            abort(400)
        user = new_user_setup(form)
        try:
            models.ExternalToken.update_token(
                user, form.external_system.data, form.external_token.data)
        except InvalidExternalSystem:
            abort(400)
        else:
            return user.get_credentials()


class TokenWS(WebService):
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
