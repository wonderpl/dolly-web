import base64
import json
import uuid
from cStringIO import StringIO
from mock import patch

from flask import Response
from flask import request
from flask import g

from test import base
from test.assets import AVATAR_IMG_DATA
from rockpack.mainsite import app
from rockpack.mainsite.core.webservice import ajax
from rockpack.mainsite.core.token import create_access_token
from rockpack.mainsite.core.oauth.decorators import check_authorization, check_client_authorization
from rockpack.mainsite.services.user.models import User
from rockpack.mainsite.services.video.models import Channel
from rockpack.mainsite.services.oauth.models import ExternalToken
from rockpack.mainsite.services.oauth import exceptions


ACCESS_CREDENTIALS = {
        "access_token": "2YotnFZFEjr1zCsicMWpAA",
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": "tGzv3JOkF0XG5Qx2TlKWIA"}


class HeadersTestCase(base.RockPackTestCase):

    def _call_url(self, client, path, headers=None,
            encoded_id=base64.encodestring(app.config['ROCKPACK_APP_CLIENT_ID'] + ':'),
            data={}):

        if headers is None:
            headers = [('Authorization', 'Basic {}'.format(encoded_id))]
        return client.post(path, headers=headers, data=data)

    @app.route('/test/oauth2/header/', methods=('GET', 'POST',))
    @ajax
    @check_client_authorization
    def some_view():
        return Response()

    def test_authentication_success(self):
        with self.app.test_client() as client:
            r = self._call_url(client, '/test/oauth2/header/?grant_type=password')
            self.assertEquals(200, r.status_code)

    def test_authentication_failed(self):

        def _error_dict(error):
            return {'error': error}

        with self.app.test_client() as client:
            r = self._call_url(client,
                    '/test/oauth2/header/?grant_type=password',
                    headers=[])
            self.assertEquals(401, r.status_code)
            self.assertEquals(_error_dict('invalid_request'), json.loads(r.data))

            r = self._call_url(client,
                    '/test/oauth2/header/?grant_type=password',
                    encoded_id=base64.encodestring('username:password'))
            self.assertEquals(401, r.status_code)
            self.assertEquals(_error_dict('unauthorized_client'), json.loads(r.data))

    @app.route('/test/oauth2/access_token_header/', methods=('GET', 'POST',))
    @check_authorization()
    def access_token_view():
        user_id = request.args.get('user_id')
        assert g.authorized.user.id == user_id
        return Response()

    def test_access_token_authentication(self):
        with self.app.test_client() as client:
            client_id = uuid.uuid4().hex
            user = self.create_test_user()
            token = create_access_token(user.id, client_id, 3600)
            r = self._call_url(client,
                    '/test/oauth2/access_token_header/?user_id={}'.format(user.id),
                    headers={'Authorization': 'Bearer {}'.format(token)})
            self.assertEquals(200, r.status_code)

    def test_failed_access_token(self):
        with self.app.test_client() as client:
            r = self._call_url(client,
                    '/test/oauth2/access_token_header/',
                    headers={'Authorization': 'Bearer {}'.format('foo')})
            self.assertEquals(401, r.status_code)


class LoginTestCase(base.RockPackTestCase):

    @patch('rockpack.mainsite.services.oauth.api.user_authenticated', return_value=User())
    def test_succesful_login(self, user_authenticated):
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


class ExternalTokenTestCase(base.RockPackTestCase):

    def _new_user(self):
        u = User(username=uuid.uuid4().hex,
                password_hash='',
                first_name='first',
                last_name='last',
                email='em@ail.com',
                avatar='',
                refresh_token='',
                is_active=True)
        return u.save()

    def test_facebook_token(self):
        user = self._new_user()
        token = uuid.uuid4().hex
        ExternalToken.update_token(user, 'facebook', token, 1111)

        e = ExternalToken.query.filter_by(external_token=token).one()
        self.assertEquals('facebook', e.external_system)
        self.assertEquals(user.username, e.user_rel.username)

        # test we can overwrite token
        new_token = uuid.uuid4().hex
        ExternalToken.update_token(user, 'facebook', new_token, 1111)

        e = ExternalToken.query.filter_by(user=user.id)
        self.assertEquals(1, e.count(), 'only one token should exist')
        e = e.one()
        self.assertEquals(new_token, e.external_token, 'saved token should match new token')

    def test_invalid_token(self):
        with self.assertRaises(exceptions.InvalidExternalSystem):
            ExternalToken.update_token(None, 'HandLeaflet', None, 0000)


FACEBOOK_GRAPH_DATA = {'username': 'tony.start.01',
    'first_name': 'Tony', 'last_name': 'Stark',
    'verified': True,
    'name': 'I am IronMan',
    'locale': 'en_US',
    'gender': 'male',
    'updated_time': '2013-02-25T10:31:31+0000',
    'link': 'http://www.facebook.com/tony.stark.01',
    'timezone': 0,
    'id': '100005332297459'}


class RegisterTestCase(base.RockPackTestCase):

    @patch('rockpack.mainsite.services.oauth.api.ExternalUser._get_external_data')
    def test_facebook_registration(self, _get_external_data):
        _get_external_data.return_value = FACEBOOK_GRAPH_DATA

        with self.app.test_client() as client:
            encoded = base64.encodestring(app.config['ROCKPACK_APP_CLIENT_ID'] + ':')
            headers = [('Authorization', 'Basic {}'.format(encoded))]

            facebook_token = uuid.uuid4().hex
            r = client.post('/ws/register/external/',
                    headers=headers,
                    data=dict(
                        register='1',
                        username='facebook_user',
                        first_name='face',
                        last_name='book',
                        email='foo@bar.com',
                        external_system='facebook',
                        external_token=facebook_token))

            creds = json.loads(r.data)
            self.assertEquals(200, r.status_code)
            self.assertNotEquals(None, creds['refresh_token'])

            r = client.post('/ws/login/external/',
                    headers=headers,
                    data=dict(
                        external_system='facebook',
                        external_token=facebook_token))
            self.assertEquals(200, r.status_code)

            # TODO: test duplicate fb id

            # TODO: test duplicate username, different fb id

    @patch('rockpack.mainsite.services.oauth.api.ExternalUser._get_external_data')
    def test_invalid_external_system(self, _get_external_data):
        _get_external_data.return_value = FACEBOOK_GRAPH_DATA
        with self.app.test_client() as client:
            encoded = base64.encodestring(app.config['ROCKPACK_APP_CLIENT_ID'] + ':')
            headers = [('Authorization', 'Basic {}'.format(encoded))]

            facebook_token = uuid.uuid4().hex
            r = client.post('/ws/register/external/',
                    headers=headers,
                    data=dict(
                        external_system='PantsBake',
                        external_token=facebook_token))

            self.assertEquals(400, r.status_code)

    def test_successful_registration(self):

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

            creds = json.loads(r.data)
            self.assertEquals(200, r.status_code)
            self.assertNotEquals(None, creds['refresh_token'])
            self.assertEquals(1,
                    Channel.query.filter_by(owner_rel=User.get_from_username('foobarbarbar')).count(),
                    'default user channel should be created')

            creds = json.loads(r.data)

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
