import base64
from mock import Mock, patch

from test import base


ACCESS_CREDENTIALS = {
        "access_token": "2YotnFZFEjr1zCsicMWpAA",
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": "tGzv3JOkF0XG5Qx2TlKWIA"
        }


DUMMY_CLIENT_ID = 'this_is_a_client_id'


class LoginTestCase(base.RockPackTestCase):

    @patch('rockpack.mainsite.services.oauth.api.AuthToken.store_refresh_token')
    @patch('rockpack.mainsite.services.oauth.api.user_authenticated')
    @patch('rockpack.mainsite.services.oauth.api.validate_client_id')
    def test_succesful_login(self, validate_client_id, user_authenticated, store_refresh_token):
        validate_client_id = Mock()
        validate_client_id.return_value = True

        user_authenticated = Mock()
        user_authenticated.return_value = True

        store_refresh_token = Mock()
        store_refresh_token.return_value = None

        with self.app.test_client() as client:
            encoded = base64.encodestring(DUMMY_CLIENT_ID + ':')
            headers = [('Authorization', 'Basic {}'.format(encoded))]
            r = client.post('/ws/login/',
                    headers=headers,
                    data=dict(
                grant_type='password',
                username='foo',
                password='bar'))

            self.assertEquals(200, r.status_code)
