import uuid
import re
from flask import request
from flask import abort
from flask.ext import wtf
import facebook
from rockpack.mainsite import app
from rockpack.mainsite.core.oauth.decorators import check_client_authorization
from rockpack.mainsite.core.webservice import WebService
from rockpack.mainsite.core.webservice import expose_ajax
from rockpack.mainsite.services.video.models import Channel
from rockpack.mainsite.services.user.models import User
from . import models
from .exceptions import InvalidExternalSystem
from .exceptions import InvalidExternalToken


def user_authenticated(username, password):
    user = User.get_from_username(username)
    if user and user.check_password(password):
        return user
    return False


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
        user = models.ExternalToken.user_from_token(
                request.form.get('external_system'),
                request.form.get('external_token'))
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


class ExternalRegistrationForm(wtf.Form):
    external_system = wtf.TextField(validators=[wtf.Required()])
    external_token = wtf.TextField(validators=[wtf.Required()])

    def validate_external_system(form, value):
        if value in models.EXTERNAL_SYSTEM_NAMES:
            return wtf.ValidationError('external system invalid')


class UIDForExternalTokenExistsError(Exception):
    pass


def new_user_setup(username, first_name='', last_name='', email='', password=None, avatar='',
        external_system='', external_token='', external_uid=''):
    """ Creates a new user and sets up
        and related assets, like default channels """

    if models.ExternalToken.query.filter_by(external_uid=external_uid).count():
        raise UIDForExternalTokenExistsError('Token for ')

    user = User(
        username=username,
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash='',
        refresh_token=uuid.uuid4().hex,
        avatar=avatar,
        is_active=True)
    user = user.save()
    if password:
        user.set_password(password)

    title, description, cover = app.config['FAVOURITE_CHANNEL']
    channel = Channel(
        title=title,
        description=description,
        cover=cover,
        owner=user.id)
    channel.save()

    if external_system and external_token and external_uid:
        models.ExternalToken.update_token(
            user, external_system, external_token, external_uid)

    return user


class ExternalUser:
    valid_token = False

    def __init__(self, token):
        self._user_data = {}
        self.token = token
        try:
            graph = facebook.GraphAPI(token)
        except facebook.GraphAPIError:
            return
        else:
            self.valid_token = True
            self._user_data = graph.get_object('me')

    id = property(lambda x: x._user_data.get('id'))
    username = property(lambda x: x._user_data.get('username'))
    first_name = property(lambda x: x._user_data.get('first_name', ''))
    last_name = property(lambda x: x._user_data.get('last_name', ''))
    display_name = property(lambda x: x._user_data.get('name', ''))


def sanitise_or_suggest_username(name):
    new_name = re.sub(r'\W+', '', name)
    if User.query.filter_by(username=new_name).count():
        user = User.query.filter(User.username.like('{}%'.format(new_name))).order_by("username desc").first()
        match = re.findall(r"[a-zA-Z]+|\d+", user.username)
        try:
            postfix_number = int(match[-1])
        except TypeError:
            new_name = match + '1'
        else:
            new_name = ''.join(match[:-1]) + str(postfix_number + 1)
    return new_name


class Registration(WebService):
    endpoint = '/register'

    @expose_ajax('/', methods=['POST'])
    @check_client_authorization
    def register(self):
        form = RockRegistrationForm(request.form, csrf_enabled=False)
        if not form.validate():
            abort(400, form_errors=form.errors)
        user = new_user_setup(
                username=form.username.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                email=form.email.data,
                password=form.password.data
                )
        return user.get_credentials()

    @expose_ajax('/external/', methods=['POST'])
    @check_client_authorization
    def external(self):
        from flask import g
        form = ExternalRegistrationForm(request.form, csrf_enabled=False)
        if form.validate():
            eu = ExternalUser(form.external_token.data)
            if eu.valid_token:
                try:
                    user = new_user_setup(
                            username=sanitise_or_suggest_username(eu.username),
                            first_name=eu.first_name,
                            last_name=eu.last_name,
                            external_system=form.external_system.data,
                            external_token=form.external_token.data,
                            external_uid=eu.id,
                            )
                    return user.get_credentials()
                except UIDForExternalTokenExistsError:
                    abort(400, message='User is already registered for {} account'.format(form.external_system.data))
                except:
                    g.session.rollback()
                    raise
        abort(400)


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
