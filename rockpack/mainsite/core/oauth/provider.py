import json
from datetime import datetime
import flask
from flask.ext import login
from pyoauth2.provider import AuthorizationProvider, ResourceProvider


class RockpackAppSettings(object):
    redirect_uri = ''
    secret = '368c68dca9fc5b526fd6575c0b775476'
    client_id = 'rockpack_h78nf34oqln3594aqf418e'


class SQLAAppSettingsProxy(object):

    def find(self, client_id):
        if client_id == RockpackAppSettings.client_id:
            return RockpackAppSettings
        return None


class TokenMapper(object):

    def set_auth_token(self, key, expires, data):
        raise NotImplementedError('Subclass must implement set_auth_token')

    def get_auth_token(self, key):
        """ Returns a tuple of either empty
            or (expiry, data) """
        raise NotImplementedError('Subclass must implement get_auth_token')

    def delete_auth_token(self, key):
        raise NotImplementedError('Subclass must implement delete_auth_token')

    def set_access_refresh_pair(self, key, access_key, refresh_key):
        raise NotImplementedError('Subclass must implement set_access_refresh_pair')

    def delete_access_refresh_pair(self, key):
        raise NotImplementedError('Subclass must implement delete_access_refresh_pair')


class RockpackAuthorisationProvider(AuthorizationProvider):
    def __init__(self, settings_engine, key_store):
        self.app_settings = settings_engine
        self.store = key_store

    def validate_client_id(self, client_id):
        return self.app_settings.find(client_id)

    def validate_client_secret(self, client_id, client_secret):
        app = self.app_settings.find(client_id)
        if app is not None and app.secret == client_secret:
            return True
        return False

    def validate_redirect_uri(self, client_id, redirect_uri):
        app = self.app_settings.find(client_id)

        if app is not None and app.redirect_uri == redirect_uri.split('?')[0]:
            return True
        return False

    def validate_access(self):
        return not login.current_user.is_anonymous() or login.current_user.is_active()

    def validate_scope(self, client_id, scope):
        return True if scope == '' else False

    def persist_authorization_code(self, client_id, code, scope):
        key = 'oauth2.authorization_code.%s:%s' % (client_id, code)
        data = {'client_id': client_id,
                'scope': scope,
                'user_id': flask.session.user_id}

        self.store.set_auth_token(key, 60, json.dumps(data))

    def persist_token_information(self, client_id, scope, access_token,
            token_type, expires_in, refresh_token, data):

        # Set access token with proper expiration
        access_key = 'oauth2.access_token:%s' % access_token
        self.store.set_auth_token(access_key, expires_in, json.dumps(data))

        # Set refresh token with no expiration
        refresh_key = 'oauth2.refresh_token.%s:%s' % (client_id, refresh_token)
        self.store.set_auth_token(refresh_key, -1, json.dumps(data))

        # Associate tokens to user for easy token revocation per app user
        key = 'oauth2.client_user.%s:%s' % (client_id, data.get('user_id'))
        self.store.set_access_refresh_pair(key, access_key, refresh_key)

    def from_authorization_code(self, client_id, code, scope):
        key = 'oauth2.authorization_code.%s:%s' % (client_id, code)
        _, data = self.store.get_auth_token(key)
        if data is not None:
            data = json.loads(data)

            if (scope == '' or scope == data.get('scope')) and \
                    data.get('client_id') == client_id:
                return data
        return None

    def from_refresh_token(self, client_id, refresh_token, scope):
        key = 'oauth2.refresh_token.%s:%s' % (client_id, refresh_token)
        _, data = self.store.get_auth_token(key)
        if data is not None:
            data = json.loads(data)

            if (scope == '' or scope == data.get('scope')) and \
                    data.get('client_id') == client_id:
                return data
        return None

    def discard_authorization_code(self, client_id, code):
        key = 'oauth2.authorization_code.%s:%s' % (client_id, code)
        self.store.delete_auth_token(key)

    def discard_refresh_token(self, client_id, refresh_token):
        key = 'oauth2.refresh_token.%s:%s' % (client_id, refresh_token)
        self.store.delete_auth_token(key)

    def discard_client_user_tokens(self, client_id, user_id):
        key = 'oauth2.client_user.%s:%s' % (client_id, user_id)
        self.store.delete_access_refresh_pair(key)


class RockpackResourceProvider(ResourceProvider):

    def __init__(self, store):
        self.store = store

    def get_authorization_header(self):
        return flask.request.headers.get('Authorization', None)

    def validate_access_token(self, access_token, authorization):
        try:
            expires, raw_json = self.store.get_auth_token('oauth2.access_token:{}'.format(access_token))
        except ValueError:
            return
        now = datetime.now()
        if now > expires:
            return
        data = json.loads(raw_json)
        authorization.is_valid = True
        authorization.client_id = data['client_id']
        authorization.expires_in = (expires - now).total_seconds()
