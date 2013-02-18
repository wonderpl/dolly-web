import base64
from cStringIO import StringIO
from mock import Mock, patch

from test import base
from test.assets import AVATAR_IMG_PATH
from rockpack.mainsite import app


ACCESS_CREDENTIALS = {
        "access_token": "2YotnFZFEjr1zCsicMWpAA",
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": "tGzv3JOkF0XG5Qx2TlKWIA"}


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
                        grant_type='password',
                        register='1',
                        username='foobar',
                        password='bar',
                        first_name='foo',
                        last_name='bar',
                        email='foo@bar.com',
                        avatar=(StringIO(AVATAR_IMG_PATH), 'avatar.jpg',)))

            self.assertEquals(201, r.status_code)
