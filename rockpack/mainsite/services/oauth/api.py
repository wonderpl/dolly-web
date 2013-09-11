from werkzeug.datastructures import MultiDict
from datetime import datetime, timedelta
from cStringIO import StringIO
from flask import request, abort, g, json
from flask.ext import wtf
from rockpack.mainsite import app, requests
from rockpack.mainsite.helpers import lazy_gettext as _
from rockpack.mainsite.helpers.forms import naughty_word_validator
from rockpack.mainsite.helpers.db import get_column_property, get_column_validators
from rockpack.mainsite.helpers.urls import url_for
from rockpack.mainsite.core.token import create_access_token
from rockpack.mainsite.core.email import send_email, env as email_env
from rockpack.mainsite.core.oauth.decorators import check_client_authorization
from rockpack.mainsite.core.webservice import WebService, expose_ajax
from rockpack.mainsite.services.user.models import User, UserAccountEvent, username_exists, GENDERS
from rockpack.mainsite.services.video.models import Locale
from . import facebook, models


def record_user_event(username, type, value=''):
    trunc = lambda f, v: v[:get_column_property(UserAccountEvent, f, 'length')]
    try:
        clientid = g.app_client_id or g.authorized.clientid
        userid = g.authorized.userid
    except AttributeError:
        clientid = ''
        userid = None
    UserAccountEvent(
        user=userid,
        username=trunc('username', username or '-'),
        event_type=type,
        event_value=value,
        ip_address=request.remote_addr or '',
        user_agent=trunc('user_agent', request.user_agent.string),
        clientid=clientid,
    ).save()


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
            record_user_event(request.form['username'], 'login failed')
            abort(400, error='invalid_grant')
        record_user_event(request.form['username'], 'login succeeded', user.id)
        return user.get_credentials()

    @expose_ajax('/external/', methods=['POST'])
    @check_client_authorization
    def external(self):
        form = ExternalRegistrationForm(csrf_enabled=False)
        if not form.validate():
            abort(400, form_errors=form.errors)

        result = {}

        eu = ExternalUser(**form.data)
        if not eu.token_is_valid:
            abort(400, error='unauthorized_client')

        user = models.ExternalToken.user_from_uid(eu.system, eu.id)

        if user:
            record_user_event(user.username, 'login succeeded', user.id)
        else:
            # New user
            user = User.create_from_external_system(eu, self.get_locale())
            record_user_event(user.username, 'registration succeeded', user.id)
            result['registered'] = True

        # Update the token record if needed
        models.ExternalToken.update_token(user.id, eu)

        result.update(user.get_credentials())
        return result


def username_validator():
    def _valid(form, field):
        if not field.data:
            return
        if field.data != User.sanitise_username(field.data):
            raise wtf.ValidationError(_('Username can only contain alphanumerics.'))
        exists = username_exists(field.data)
        if exists == 'reserved':
            raise wtf.ValidationError(_('"%s" is reserved.') % field.data)
        elif exists:
            raise wtf.ValidationError(_('"%s" already taken.') % field.data)
        naughty_word_validator(form, field)
    return _valid


def email_validator():
    # Additional address validation for SES - doesn't like foo@bar.com. or foo@bar..com
    def _valid(form, field):
        if not field.data:
            return
        if field.data.endswith('.') or ' ' in field.data or '..' in field.data.rsplit('@', 1)[-1]:
            raise wtf.ValidationError(_('Invalid email address.'))
    return _valid


def email_registered_validator():
    def _registered(form, field):
        if User.query.filter_by(email=field.data).count():
            raise wtf.ValidationError(_('Email address already registered.'))
    return _registered


def gender_validator():
    def _valid(form, field):
        if field.data not in GENDERS:
            raise wtf.ValidationError(_('Invalid gender.'))
    return _valid


def date_of_birth_validator():
    def _valid(form, value):
        if value.data:
            delta = (datetime.today().date() - value.data).days / 365.0
            if delta > 150:
                raise wtf.ValidationError(_("Looks like you're unreasonably old!"))
            elif delta < 0:
                raise wtf.ValidationError(_("Looks like you're born in the future!"))
            elif delta < 13:
                raise wtf.ValidationError(_("Rockpack is not available for under 13's yet."))
    return _valid


class RockRegistrationForm(wtf.Form):
    username = wtf.TextField(validators=[wtf.Length(min=3), username_validator()] + get_column_validators(User, 'username'))
    password = wtf.PasswordField(validators=[wtf.Required(), wtf.Length(min=6)])
    first_name = wtf.TextField(validators=[wtf.Optional()] + get_column_validators(User, 'first_name'))
    last_name = wtf.TextField(validators=[wtf.Optional()] + get_column_validators(User, 'last_name'))
    gender = wtf.TextField(validators=[wtf.Optional(), gender_validator()] + get_column_validators(User, 'gender'))
    date_of_birth = wtf.DateField(validators=[date_of_birth_validator()] + get_column_validators(User, 'date_of_birth'))
    locale = wtf.TextField(validators=get_column_validators(User, 'locale'))
    email = wtf.TextField(validators=[wtf.Email(), email_validator(), email_registered_validator()] + get_column_validators(User, 'email'))


class ExternalRegistrationForm(wtf.Form):
    external_system = wtf.TextField(validators=[wtf.Required()])
    external_token = wtf.TextField(validators=[wtf.Required()])
    token_expires = wtf.TextField()
    token_permissions = wtf.TextField()
    meta = wtf.TextField()

    def validate_external_system(form, value):
        if value.data not in models.EXTERNAL_SYSTEM_NAMES:
            raise wtf.ValidationError(_('External system invalid.'))

    def validate_token_expires(form, value):
        if value.data:
            try:
                value.data = datetime.strptime(value.data[:19], '%Y-%m-%dT%H:%M:%S')
            except ValueError:
                raise wtf.ValidationError(_('Invalid expiry date.'))

    def validate_meta(form, value):
        if value.data:
            try:
                if isinstance(value.data, basestring):
                    value.data = json.loads(value.data)
                assert type(value.data) is dict
            except:
                raise wtf.ValidationError(_('Invalid account metadata.'))


class AbstractTokenManager(object):
    def __init__(self, external_system, external_token, token_expires=None, **kwargs):
        self._token = external_token
        self._system = external_system

        if type(token_expires) is int:
            self._expires = datetime.now() + timedelta(seconds=token_expires)
        else:
            if not token_expires and isinstance(token_expires, (str, unicode)):
                self._expires = None
            else:
                self._expires = token_expires

    def token_is_valid(self):
        raise NotImplementedError

    def get_new_token(self):
        raise NotImplementedError

    @staticmethod
    def is_handler_for(external_system):
        raise NotImplementedError

    @property
    def permissions(self):
        raise NotImplementedError

    @property
    def meta(self):
        raise NotImplementedError

    @property
    def token(self):
        return self._token

    @property
    def system(self):
        return self._system

    @property
    def expires(self):
        return self._expires


class APNSTokenManager(AbstractTokenManager):
    @staticmethod
    def is_handler_for(external_system):
        return external_system == 'apns'

    def get_new_token(self):
        return self

    @property
    def id(self):
        return g.authorized.userid

    @property
    def permissions(self):
        return ''

    @property
    def meta(self):
        return ''


# TODO: currently only Facebook
# TODO: subclass this for each social account type
class ExternalUser(AbstractTokenManager):
    def __init__(self, external_system, external_token, token_expires, token_permissions=None, meta=None):
        super(ExternalUser, self).__init__(external_system, external_token, token_expires)

        self._valid_token = False

        if not token_expires and not token_permissions:
            data = self._validate_token()
            if not data:
                return  # invalid token

            token_expires = datetime.fromtimestamp(data['expires_at'])
            token_permissions = ','.join(data['scopes'])
            meta = data.get('metadata')

        self._permissions = token_permissions
        self._meta = json.dumps(meta) if meta else None

        self._user_data = self._get_external_data()
        if self._user_data:
            self._valid_token = True
        else:
            abort(400, error='unauthorized_client')

    def _validate_token(self):
        try:
            return facebook.validate_token(
                self._token,
                app.config['FACEBOOK_APP_ID'],
                app.config['FACEBOOK_APP_SECRET'])
        except:
            app.logger.exception('Failed to validate Facebook token')

    def _get_external_data(self):
        try:
            return facebook.GraphAPI(self._token).get_object('me')
        except facebook.GraphAPIError:
            pass
        return {}

    @staticmethod
    def is_handler_for(external_system):
        return external_system == 'facebook'

    def get_new_token(self):
        token, expires = facebook.renew_token(
            self._token,
            app.config['FACEBOOK_APP_ID'],
            app.config['FACEBOOK_APP_SECRET'])
        return self.__class__(self.system, token, expires)

    id = property(lambda x: x._user_data.get('id'))
    username = property(lambda x: x._user_data.get('username'))
    first_name = property(lambda x: x._user_data.get('first_name', ''))
    last_name = property(lambda x: x._user_data.get('last_name', ''))
    display_name = property(lambda x: x._user_data.get('name', ''))

    @property
    def meta(self):
        return self._meta

    @property
    def permissions(self):
        return self._permissions

    @property
    def token_is_valid(self):
        return self._valid_token

    @property
    def email(self):
        if 'email' in self._user_data:
            return self._user_data['email']
        elif 'username' in self._user_data:
            return '%s@facebook.com' % self._user_data['username']
        else:
            return ''

    @property
    def gender(self):
        if 'gender' in self._user_data:
            try:
                g = self._user_data['gender'].strip()[0]
            except IndexError:
                pass
            else:
                if g.lower() in GENDERS:
                    return g

    @property
    def dob(self):
        try:
            dob = self._user_data['birthday']
            month, day, year = map(int, dob.split('/'))
            return datetime(month=month, day=day, year=year)
        except KeyError:
            return None

    @property
    def locale(self):
        l = self._user_data.get('locale', '').lower().replace('_', '-')
        if not Locale.query.get(l):
            return ''
        return l

    @property
    def avatar(self):
        r = requests.get(facebook.FACEBOOK_PICTURE_URL % self.id)
        if r.status_code == 200 and r.headers.get('content-type', '').startswith('image/'):
            return StringIO(r.content)
        return ''


def ExternalTokenManager(external_system, external_token, **kwargs):
    """ Factory for selecting a Token Manager """
    for cls in AbstractTokenManager.__subclasses__():
        if cls.is_handler_for(external_system):
            return cls(external_system, external_token, **kwargs)


class RegistrationWS(WebService):
    endpoint = '/register'

    @expose_ajax('/', methods=['POST'])
    @check_client_authorization
    def register(self):
        form = RockRegistrationForm(csrf_enabled=False)
        if not form.validate():
            record_user_event(form.username.data, 'registration failed',
                              ','.join(form.errors.keys()))
            abort(400, form_errors=form.errors)
        user = User.create_with_channel(
            username=form.username.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            date_of_birth=form.date_of_birth.data,
            email=form.email.data,
            password=form.password.data,
            gender=form.gender.data or None,
            locale=form.locale.data)
        record_user_event(user.username, 'registration succeeded', user.id)
        return user.get_credentials()

    @expose_ajax('/availability/', methods=['POST'])
    @check_client_authorization
    def check_availability(self):
        value = request.form.get('username', '')
        form = RockRegistrationForm(formdata=MultiDict([('username', value)]), csrf_enabled=False)
        if not form.username:
            abort(400, message='No data given.')
        if not form.username.validate(form.username.data):
            for error in form.username.errors:
                if u'"{}" already taken'.format(value) in error:
                    return {"available": False}

            response = {'message': form.username.errors}
            abort(400, **response)

        return {"available": True}


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
            record_user_event('', 'refresh token failed')
            abort(400, error='invalid_grant')
        record_user_event(user.username, 'refresh token succeeded', user.id)
        return user.get_credentials()


def send_password_reset(user):
    if not user.email:
        app.logger.warning("Can't reset password for %s: no email address", user.id)
        return
    token = create_access_token(user.id, '', 86400)
    url = url_for('reset_password') + '?token=' + token
    template = email_env.get_template('reset.html')
    subject = 'Rockpack password reset'
    body = template.render(
        reset_link=url,
        subject=subject,
        username=user.username,
        email=user.email,
        email_sender=app.config['DEFAULT_EMAIL_SOURCE'],
        assets=app.config.get('ASSETS_URL', '')
    )
    send_email(user.email, subject, body, format='html')


class ResetWS(WebService):

    endpoint = '/reset-password'

    @expose_ajax('/', methods=['POST'])
    @check_client_authorization
    def reset_password(self):
        user = User.get_from_credentials(request.form['username'], None)
        if not user:
            abort(400)
        record_user_event(user.username, 'password reset requested')
        # TODO: move to offline process
        send_password_reset(user)
