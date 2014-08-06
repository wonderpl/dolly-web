from werkzeug.datastructures import MultiDict
from datetime import datetime, timedelta
from cStringIO import StringIO
from sqlalchemy.exc import IntegrityError
import wtforms as wtf
from flask import request, abort, g, json
from flask.ext.wtf import Form
from rockpack.mainsite import app, requests
from rockpack.mainsite.helpers import lazy_gettext as _
from rockpack.mainsite.helpers.forms import naughty_word_validator
from rockpack.mainsite.helpers.db import get_column_property, get_column_validators
from rockpack.mainsite.helpers.urls import url_for
from rockpack.mainsite.core.dbapi import commit_on_success, db
from rockpack.mainsite.core.token import create_access_token
from rockpack.mainsite.core.email import send_email, env as email_env
from rockpack.mainsite.core.oauth.decorators import check_client_authorization
from rockpack.mainsite.core.webservice import WebService, expose_ajax, secure_view
from rockpack.mainsite.background_sqs_processor import background_on_sqs
from rockpack.mainsite.services.user.models import User, UserAccountEvent, username_exists, GENDERS
from rockpack.mainsite.services.video.models import Locale
from . import facebook, models
import twitter


def record_user_event(username, type, value='', user=None, commit=False):
    trunc = lambda f, v: v[:get_column_property(UserAccountEvent, f, 'length')]
    try:
        clientid = g.app_client_id or g.authorized.clientid
    except AttributeError:
        clientid = ''
    event = UserAccountEvent(
        username=trunc('username', username or '-'),
        event_type=type,
        event_value=value,
        ip_address=request.remote_addr or '',
        user_agent=trunc('user_agent', request.user_agent.string),
        clientid=clientid,
    )
    if user:
        event.user_rel = user
    if commit:
        event.save()
    else:
        event.add()
    return event


if app.config.get('TEST_EXTERNAL_SYSTEM'):
    @app.route('/test/fb/login/', subdomain=app.config.get('SECURE_SUBDOMAIN'))
    def test_fb():
        from flask import render_template
        from test.test_helpers import get_client_auth_header
        return render_template('fb_test.html',
                               client_auth_headers=[get_client_auth_header()])


@commit_on_success
def _register_user(form):
    user = User.create_with_channel(
        username=form.username.data,
        first_name=form.first_name.data,
        last_name=form.last_name.data,
        date_of_birth=form.date_of_birth.data,
        email=form.email.data.lower(),
        password=form.password.data,
        gender=form.gender.data or None,
        locale=form.locale.data)
    record_user_event(user.username, 'registration succeeded', user=user)

    # Check if anyone has emailed this person before
    senders = models.ExternalFriend.query.filter(
        models.ExternalFriend.external_system == 'email',
        models.ExternalFriend.email == user.email
    ).join(
        User,
        User.id == models.ExternalFriend.user
    ).with_entities(User)

    if senders.count():
        db.session.flush()  # Get the user id before the commit
        from rockpack.mainsite.services.share import api
        for sender in senders:
            api.create_reverse_email_friend_association(sender, user)

    return user


@commit_on_success
def _login(username, password):
    user = User.get_from_credentials(username, password)
    if not user:
        record_user_event(username, 'login failed', commit=True)
        abort(400, error='invalid_grant')
    record_user_event(username, 'login succeeded', user=user)
    return user


@commit_on_success
def _external_login(external_user, locale):
    user = models.ExternalToken.user_from_uid(external_user.system, external_user.id)

    if user and not user.is_active:
        record_user_event(user.username, 'login failed', user=user, commit=True)
        abort(400, error='invalid_grant')

    if user:
        record_user_event(user.username, 'login succeeded', user=user)
        registered = False
    else:
        # New user
        user = User.create_from_external_system(external_user, locale)
        record_user_event(user.username, 'registration succeeded', user=user)
        registered = True

    # Update the token record if needed
    models.ExternalToken.update_token(user, external_user)

    return user, registered


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
        if field.data:
            field.data = field.data.lower()
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


@background_on_sqs
def send_password_reset(userid):
    user = User.query.get(userid)
    if not user.email:
        app.logger.warning("Can't reset password for %s: no email address", user.id)
        return

    token = create_access_token(user.id, '', 86400)
    url = url_for('reset_password') + '?token=' + token
    template = email_env.get_template('reset.html')
    body = template.render(
        reset_link=url,
        user=user,
        email_sender=app.config['DEFAULT_EMAIL_SOURCE'],
    )
    send_email(user.email, body)


class RockRegistrationForm(Form):
    username = wtf.TextField(validators=[wtf.validators.Length(min=3), username_validator()] + get_column_validators(User, 'username'))
    password = wtf.PasswordField(validators=[wtf.validators.Required(), wtf.validators.Length(min=6)])
    first_name = wtf.TextField(validators=[wtf.validators.Optional()] + get_column_validators(User, 'first_name'))
    last_name = wtf.TextField(validators=[wtf.validators.Optional()] + get_column_validators(User, 'last_name'))
    gender = wtf.TextField(validators=[wtf.validators.Optional(), gender_validator()] + get_column_validators(User, 'gender'))
    date_of_birth = wtf.DateField(validators=[date_of_birth_validator()] + get_column_validators(User, 'date_of_birth'))
    locale = wtf.TextField(validators=get_column_validators(User, 'locale'))
    email = wtf.TextField(validators=[wtf.validators.Email(), email_validator(), email_registered_validator()] + get_column_validators(User, 'email'))
    description = wtf.TextField(validators=[wtf.validators.Optional()] + get_column_validators(User, 'description'))


class ExternalRegistrationForm(Form):
    external_system = wtf.TextField(validators=[wtf.validators.Required()])
    external_token = wtf.TextField(validators=[wtf.validators.Required()])
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


class ExternalUser(AbstractTokenManager):

    @staticmethod
    def is_handler_for(external_system):
        return False

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

    id = property(lambda x: str(x._user_data['id']) if 'id' in x._user_data else None)
    username = property(lambda x: x._user_data.get('username'))
    first_name = property(lambda x: x._user_data.get('first_name', ''))
    last_name = property(lambda x: x._user_data.get('last_name', ''))
    display_name = property(lambda x: x._user_data.get('name', ''))
    email = property(lambda x: x._user_data.get('email', ''))
    description = property(lambda x: x._user_data.get('description', ''))

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


class FacebookUser(ExternalUser):

    @staticmethod
    def is_handler_for(external_system):
        return external_system == 'facebook'

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

    def get_new_token(self):
        token, expires = facebook.renew_token(
            self._token,
            app.config['FACEBOOK_APP_ID'],
            app.config['FACEBOOK_APP_SECRET'])
        return self.__class__(self.system, token, expires)

    @property
    def email(self):
        email = super(FacebookUser, self).email
        if not email and 'username' in self._user_data:
            email = '%s@facebook.com' % self._user_data['username']
        return email

    @property
    def avatar(self):
        r = requests.get(facebook.FACEBOOK_PICTURE_URL % self.id)
        if r.status_code == 200 and r.headers.get('content-type', '').startswith('image/'):
            return StringIO(r.content)
        return ''


class TwitterUser(ExternalUser):

    @staticmethod
    def is_handler_for(external_system):
        return external_system == 'twitter'

    def _verify(self):
        if not hasattr(self, '_verification_data'):
            try:
                token_key, token_secret = self._token.split(':', 1)
            except ValueError:
                self._verification_data = None
            else:
                api = twitter.Api(
                    consumer_key=app.config['TWITTER_CONSUMER_KEY'],
                    consumer_secret=app.config['TWITTER_CONSUMER_SECRET'],
                    access_token_key=token_key,
                    access_token_secret=token_secret,
                )
                try:
                    data = api.VerifyCredentials()
                except twitter.TwitterError as e:
                    if e.message[0]['code'] in (89, 32, 215):    # Invalid or expired token
                        self._verification_data = None
                    else:
                        raise
                else:
                    self._verification_data = data.AsDict()
        return self._verification_data

    def _get_external_data(self):
        return self._verify()

    def _validate_token(self):
        data = self._verify()
        if not data:
            return
        static_data = dict(
            expires_at=4102444800,  # Twitter tokens don't expire
            scopes=['read'],        # set at app configuration
            metadata=dict(screen_name=data['screen_name']),
        )
        return dict(static_data.items() + data.items())

    def get_new_token(self):
        return self

    username = property(lambda x: x._user_data.get('screen_name'))
    first_name = property(lambda x: x._user_data.get('name'))
    cover_image = property(lambda x: x._user_data.get('profile_background_image_url'))

    @property
    def avatar(self):
        image_url = self._user_data['profile_image_url'].replace('_normal.', '.')
        r = requests.get(image_url)
        if r.status_code == 200 and r.headers.get('content-type', '').startswith('image/'):
            return StringIO(r.content)
        return ''


class RomeoUser(ExternalUser):

    @staticmethod
    def is_handler_for(external_system):
        return external_system == 'romeo'

    def _get_external_data(self):
        r = requests.get(app.config['ROMEO_ACCOUNT_VERIFY_URL'],
                         allow_redirects=False,
                         cookies=dict(romeo=self.token))
        if r.status_code == 200:
            return r.json()

    def get_new_token(self):
        # All Romeo tokens are long lived
        return self

    avatar = ''


def ExternalTokenManager(external_system, external_token, **kwargs):
    """ Factory for selecting a Token Manager """
    for cls in AbstractTokenManager.__subclasses__() + ExternalUser.__subclasses__():
        if cls.is_handler_for(external_system):
            return cls(external_system, external_token, **kwargs)


class LoginWS(WebService):

    endpoint = '/login'

    @expose_ajax('/', methods=['POST'])
    @check_client_authorization
    def login(self):
        if not request.form['grant_type'] == 'password':
            abort(400, error='unsupported_grant_type')
        user = _login(request.form['username'], request.form['password'])
        return user.get_credentials()

    @expose_ajax('/external/', methods=['POST'])
    @check_client_authorization
    def external(self):
        form = ExternalRegistrationForm(csrf_enabled=False)
        if not form.validate():
            abort(400, form_errors=form.errors)

        external_user = ExternalTokenManager(**form.data)
        if not (external_user and external_user.token_is_valid):
            abort(400, error='unauthorized_client')

        # Since the call to Facebook to validate the token can take a while, it's
        # possible that another login request could come in here, in which case we
        # retry once - the first should return a registered=True and second a False.
        for retry in 1, 0:
            try:
                user, registered = _external_login(external_user, self.get_locale())
            except (models.TokenExistsException, IntegrityError):
                if retry:
                    continue
                else:
                    app.logger.exception('Unable to register user: %s/%s',
                                         external_user.system, external_user.id)
                    abort(400, error='unauthorized_client')
            else:
                break

        # Return non-expiring token to Romeo
        expires_in = 0 if external_user.system == 'romeo' else None
        return dict(registered=registered, **user.get_credentials(expires_in=expires_in))


class RegistrationWS(WebService):
    endpoint = '/register'

    @expose_ajax('/', methods=['POST'])
    @check_client_authorization
    def register(self):
        form = RockRegistrationForm(csrf_enabled=False)
        if not form.validate():
            record_user_event(form.username.data, 'registration failed',
                              ','.join(form.errors.keys()), commit=True)
            abort(400, form_errors=form.errors)
        user = _register_user(form)
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
        user = User.query.filter_by(is_active=True, refresh_token=refresh_token).first()
        if not user:
            record_user_event('', 'refresh token failed', commit=True)
            abort(400, error='invalid_grant')
        record_user_event(user.username, 'refresh token succeeded', user=user, commit=True)
        return user.get_credentials()


class ResetWS(WebService):

    endpoint = '/reset-password'

    @expose_ajax('/', methods=['POST'])
    @check_client_authorization
    def reset_password(self):
        user = User.get_from_credentials(request.form['username'], None)
        if not user:
            abort(400)
        record_user_event(user.username, 'password reset requested', user=user, commit=True)
        send_password_reset(user.id)


class FacebookWS(WebService):

    endpoint = '/facebook'

    @expose_ajax('/deauth-callback', methods=['GET', 'POST'])
    @secure_view()
    def deauth_callback(self):
        try:
            data = facebook.parse_signed_cookie(
                request.form['signed_request'],
                app.config['FACEBOOK_APP_SECRET']
            )
            uid = data['user_id']
        except Exception:
            app.logger.exception('Unable to parse facebook deauth: %s', request.form)
        else:
            token = models.ExternalToken.query.filter_by(
                external_system='facebook',
                external_uid=uid
            ).first()
            if token:
                token.expires = '2001-01-01'    # sometime in the past
                token.user_rel.reset_refresh_token()
                token.save()
