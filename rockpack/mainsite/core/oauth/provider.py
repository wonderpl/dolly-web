import json
from datetime import datetime
import flask
from pyoauth2.provider import AuthorizationProvider, ResourceProvider


class RockpackAuthorisationProvider(AuthorizationProvider):
    def __init__(self, client_engine, store):
        self.rockpack_client_engine = client_engine
        self.store = store

    def validate_client_id(self, client_id):
        return self.rockpack_client_engine.find(client_id)

    def validate_client_secret(self, client_id, client_secret):
        app = self.rockpack_client_engine.find(client_id)
        if app is not None and app.secret == client_secret:
            return True
        return False

    def validate_redirect_uri(self, client_id, redirect_uri):
        app = self.rockpack_client_engine.find(client_id)

        if app is not None and app.redirect_uri == redirect_uri.split('?')[0]:
            return True
        return False

    def validate_access(self):
        return flask.session.user is not None

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
        now = datetime.utcnow()
        if now > expires:
            return
        data = json.loads(raw_json)
        authorization.is_valid = True
        authorization.client_id = data['client_id']
        authorization.expires_in = (expires - now).total_seconds()
