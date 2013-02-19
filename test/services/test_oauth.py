import base64
import json
from cStringIO import StringIO
from mock import Mock, patch

from flask import Response

from test import base
from test.assets import AVATAR_IMG_DATA
from rockpack.mainsite import app
from rockpack.mainsite.services.oauth.api import verify_authorization_header


ACCESS_CREDENTIALS = {
        "access_token": "2YotnFZFEjr1zCsicMWpAA",
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": "tGzv3JOkF0XG5Qx2TlKWIA"}


class HeadersTestCase(base.RockPackTestCase):

    def _call_url(self, client, headers=None,
            encoded_id=base64.encodestring(app.config['ROCKPACK_APP_CLIENT_ID'] + ':'),
            data={}):

        if headers is None:
            headers = [('Authorization', 'Basic {}'.format(encoded_id))]
        return client.post('/test/oauth2/header/?grant_type=password', headers=headers, data=data)

    @app.route('/test/oauth2/header/', methods=('GET', 'POST',))
    @verify_authorization_header
    def some_view():
        return Response()

    def test_authentication_success(self):
        with self.app.test_client() as client:
            r = self._call_url(client)
            self.assertEquals(200, r.status_code)

    def test_authentication_failed(self):

        def _error_dict(error):
            return {'error': error}

        with self.app.test_client() as client:
            r = self._call_url(client, headers=[])
            self.assertEquals(400, r.status_code)
            self.assertEquals(_error_dict('invalid_request'), json.loads(r.data))

            r = self._call_url(client, encoded_id=base64.encodestring('username:password'))
            self.assertEquals(401, r.status_code)
            self.assertEquals(_error_dict('unauthorized_client'), json.loads(r.data))


class LoginTestCase(base.RockPackTestCase):

    @patch('rockpack.mainsite.services.oauth.api.AuthToken.store_refresh_token')
    @patch('rockpack.mainsite.services.oauth.api.user_authenticated')
    def test_succesful_login(self, user_authenticated, store_refresh_token):
        validate_client_id = Mock()
        validate_client_id.return_value = True

        user_authenticated = Mock()
        user_authenticated.return_value = True

        store_refresh_token = Mock()
        store_refresh_token.return_value = None

        with self.app.test_client() as client:
            encoded = base64.encodestring(app.config['ROCKPACK_APP_CLIENT_ID'] + ':')
            headers = [('Authorization', 'Basic {}'.format(encoded))]
            r = client.post('/ws/login/',
                    headers=headers,
                    data=dict(
                        grant_type='password',
                        username='foo',
                        password='bar'))

            self.assertEquals(200, r.status_code)


class RegisterTestCase(base.RockPackTestCase):

    def test_successful_registration(self):
        validate_client_id = Mock()
        validate_client_id.return_value = True

        with self.app.test_client() as client:
            encoded = base64.encodestring(app.config['ROCKPACK_APP_CLIENT_ID'] + ':')
            headers = [('Authorization', 'Basic {}'.format(encoded))]

            r = client.post('/ws/register/',
                    headers=headers,
                    data=dict(
                        register='1',
                        username='foobarbarbar',
                        password='bar',
                        first_name='foo',
                        last_name='bar',
                        email='foo@bar.com',
                        avatar=(StringIO(AVATAR_IMG_DATA), 'avatar.jpg',)))

            self.assertEquals(201, r.status_code)

            r = client.post('/ws/login/',
                    headers=headers,
                    data=dict(
                        grant_type='password',
                        username='foobarbarbar',
                        password='bar'))

            creds = json.loads(r.data)
            self.assertNotEquals(None, creds['refresh_token'])

            r = client.post('/ws/token/',
                    headers=headers,
                    data=dict(refresh_token=creds['refresh_token'],
                        grant_type='refresh_token'))

            new_creds = json.loads(r.data)

            self.assertEquals('Bearer', new_creds['token_type'], 'token type should be Bearer')
            self.assertEquals(new_creds['refresh_token'], creds['refresh_token'], 'refresh tokens should be the same')
            self.assertNotEquals(new_creds['access_token'],
                    creds['access_token'],
                    'old access token should not be the same at the new one')


            # Try and get a refresh token with an invalid token
            r = client.post('/ws/token/',
                    headers=headers,
                    data=dict(refresh_token='7348957nev9o3874nqlvcfh47lmqa'))

            self.assertEquals(400, r.status_code)
