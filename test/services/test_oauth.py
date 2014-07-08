import base64
import json
import uuid
from datetime import datetime, date
from mock import patch

from flask import Response
from flask import request
from flask import g

from rockpack.mainsite import app
from rockpack.mainsite.core.webservice import ajax
from rockpack.mainsite.core.token import create_access_token
from rockpack.mainsite.core.oauth.decorators import check_authorization, check_client_authorization
from rockpack.mainsite.services.user.models import User
from rockpack.mainsite.services.video.models import Channel
from rockpack.mainsite.services.oauth.models import ExternalToken
from rockpack.mainsite.services.oauth import exceptions
from test import base
from test.test_helpers import get_client_auth_header
from test.test_helpers import get_auth_header
from test.fixtures import UserData


ACCESS_CREDENTIALS = {
    "access_token": "2YotnFZFEjr1zCsicMWpAA",
    "token_type": "Bearer",
    "expires_in": 3600,
    "refresh_token": "tGzv3JOkF0XG5Qx2TlKWIA"}


FACEBOOK_GRAPH_DATA = {
    'username': 'tony.start.01',
    'first_name': 'Tony',
    'last_name': 'Stark',
    'verified': True,
    'name': 'I am IronMan',
    'birthday': '01/01/1973',
    'locale': 'en_US',
    'gender': 'male',
    'updated_time': '2013-02-25T10:31:31+0000',
    'link': 'http://www.facebook.com/tony.stark.01',
    'timezone': 0,
    'id': '100005340012137'}


TWITTER_DATA = {
    'created_at': u'Fri Mar 08 18:11:42 +0000 2013',
    'followers_count': 1,
    'id': 1252401133,
    'lang': u'en',
    'location': u'London',
    'name': u'Paul Egan',
    'profile_background_color': u'C0DEED',
    'profile_background_image_url': u'http://abs.twimg.com/images/themes/theme1/bg.png',
    'profile_background_tile': False,
    'profile_banner_url': u'https://pbs.twimg.com/profile_banners/1252401133/1404317810',
    'profile_image_url': u'https://pbs.twimg.com/profile_images/378800000150844731/5182cbb8a688ec3f6f1f5d11bc6830c4_normal.png',
    'profile_link_color': u'0084B4',
    'profile_sidebar_fill_color': u'DDEEF6',
    'profile_text_color': u'333333',
    'protected': False,
    'screen_name': u'paulegan_rp'
}


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
            r = self._call_url(
                client,
                '/test/oauth2/header/?grant_type=password',
                headers=[]
            )
            self.assertEquals(401, r.status_code)
            self.assertEquals(_error_dict('invalid_request'), json.loads(r.data))

            r = self._call_url(
                client,
                '/test/oauth2/header/?grant_type=password',
                encoded_id=base64.encodestring('username:password')
            )
            self.assertEquals(401, r.status_code)
            self.assertEquals(_error_dict('unauthorized_client'), json.loads(r.data))

    @app.route('/test/oauth2/access_token_header/', methods=('GET', 'POST',))
    @check_authorization()
    def access_token_view():
        user_id = request.args.get('user_id')
        if app.config.get('CHECK_AUTH_ABORT_ON_FAIL', True):
            assert g.authorized.user.id == user_id
        return Response()

    def test_access_token_authentication(self):
        with self.app.test_client() as client:
            client_id = uuid.uuid4().hex
            user = self.create_test_user()
            token = create_access_token(user.id, client_id, 3600)
            r = self._call_url(
                client,
                '/test/oauth2/access_token_header/?user_id={}'.format(user.id),
                headers={'Authorization': 'Bearer {}'.format(token)}
            )
            self.assertEquals(200, r.status_code)

    def test_failed_access_token(self):
        with self.app.test_client() as client:
            r = self._call_url(
                client,
                '/test/oauth2/access_token_header/',
                headers={'Authorization': 'Bearer {}'.format('foo')}
            )
            if app.config.get('CHECK_AUTH_ABORT_ON_FAIL', True):
                self.assertEquals(401, r.status_code)


class LoginTestCase(base.RockPackTestCase):

    @patch('rockpack.mainsite.services.user.models.User.get_resource_url')
    def test_succesful_login(self, get_resource_url):
        with self.app.test_client() as client:
            r = client.post(
                '/ws/login/',
                headers=[get_client_auth_header()],
                data=dict(
                    grant_type='password',
                    username='test_user_1',
                    password='rockpack'
                )
            )
            self.assertEquals(200, r.status_code)
            get_resource_url.assert_called_with(own=True)


class ExternalTokenTestCase(base.RockPackTestCase):

    def _new_user(self):
        return User(
            username=uuid.uuid4().hex,
            password_hash='',
            first_name='first',
            last_name='last',
            date_of_birth=date(2000, 1, 1),
            email='em@ail.com',
            avatar='',
            locale='en-us',
            refresh_token='',
            is_active=True
        ).add()

    @patch('rockpack.mainsite.services.oauth.api.FacebookUser.get_new_token')
    @patch('rockpack.mainsite.services.oauth.api.FacebookUser._get_external_data')
    def test_facebook_token(self, _get_external_data, get_new_token):
        self.app.test_request_context().push()
        _get_external_data.return_value = FACEBOOK_GRAPH_DATA
        from rockpack.mainsite.services.oauth.api import FacebookUser
        long_lived_fb_token = 'fdsuioncf3w8ryl38yb7y4eius'
        get_new_token.return_value = FacebookUser('facebook', long_lived_fb_token, 3600)

        user = self._new_user()
        token = uuid.uuid4().hex
        eu = FacebookUser('facebook', token, 3600)
        eu._user_data = FACEBOOK_GRAPH_DATA.copy()
        ExternalToken.update_token(user, eu)
        self.session.commit()

        e = ExternalToken.query.filter_by(external_token=long_lived_fb_token).one()
        self.assertEquals('facebook', e.external_system)
        self.assertEquals(user.username, e.user_rel.username)

        # test we can overwrite token
        new_token = uuid.uuid4().hex
        eu = FacebookUser('facebook', new_token, 172800)
        eu._user_data = FACEBOOK_GRAPH_DATA.copy()
        ExternalToken.update_token(user, eu)
        self.session.commit()

        e = ExternalToken.query.filter_by(user=user.id)
        self.assertEquals(1, e.count(), 'only one token should exist')
        e = e.one()
        self.assertEquals(new_token, e.external_token, 'saved token should match new token')

    @patch('rockpack.mainsite.services.oauth.api.FacebookUser._get_external_data')
    def test_token_data(self, _get_external_data):
        data = FACEBOOK_GRAPH_DATA.copy()
        data['id'] = uuid.uuid4().hex
        _get_external_data.return_value = data
        from rockpack.mainsite.services.oauth.api import FacebookUser
        expires = datetime(2020, 1, 1, 0, 0, 0)
        eu = FacebookUser('facebook', 'xxx123', expires, 'read,write', {'meta': 'data'})
        user = self._new_user()
        ExternalToken.update_token(user, eu)
        self.session.commit()
        e = ExternalToken.query.filter_by(user=user.id).one()
        self.assertEquals(e.expires, expires)
        self.assertEquals(e.permissions, 'read,write')
        self.assertEquals(e.meta, '{"meta": "data"}')

    @patch('rockpack.mainsite.services.oauth.api.FacebookUser._get_external_data')
    def test_invalid_token(self, _get_external_data):
        _get_external_data.return_value = FACEBOOK_GRAPH_DATA
        from rockpack.mainsite.services.oauth.api import FacebookUser
        eu = FacebookUser('handleaflet', '', 3600)
        with self.assertRaises(exceptions.InvalidExternalSystem):
            ExternalToken.update_token(None, eu)


class RegisterTestCase(base.RockPackTestCase):

    @patch('rockpack.mainsite.services.oauth.api.FacebookUser.get_new_token')
    @patch('rockpack.mainsite.services.oauth.api.FacebookUser._get_external_data')
    def test_facebook_login_registration(self, _get_external_data, get_new_token):
        """ Registration and login is handled in the same view.

            If a facebook token validates on their end, and we don't have a record
            for it on our end, we register the user and return an access token.
            If the user already exists on our system, we return and access token."""

        data = FACEBOOK_GRAPH_DATA.copy()
        data['id'] = uuid.uuid4().hex
        _get_external_data.return_value = data
        from rockpack.mainsite.services.oauth.api import FacebookUser
        long_lived_fb_token = 'fdsuioncf3w8ryl38yb7yfsfsdfsd4eius'
        get_new_token.return_value = FacebookUser('facebook', long_lived_fb_token, 3600)

        with self.app.test_client() as client:
            self.app.test_request_context().push()
            initial_fb_token = uuid.uuid4().hex
            r = client.post(
                '/ws/login/external/',
                headers=[get_client_auth_header()],
                data=dict(
                    external_system='facebook',
                    external_token=initial_fb_token,
                    token_expires=datetime.now().isoformat(),
                )
            )
            creds = json.loads(r.data)
            self.assertEquals(200, r.status_code)
            self.assertNotEquals(None, creds['refresh_token'])

            et = ExternalToken.query.filter_by(
                external_system='facebook',
                external_token=long_lived_fb_token)

            self.assertEquals(1, et.count(), 'should only be one token for user')
            uid = et.one().user
            self.assertEquals(User.query.get(uid).gender, 'm')

            # We pretend that the new token represents the same user,
            # so we should still get a valid login
            new_facebook_token = uuid.uuid4().hex
            r = client.post(
                '/ws/login/external/',
                headers=[get_client_auth_header()],
                data=dict(
                    external_system='facebook',
                    external_token=new_facebook_token,
                    token_expires=datetime.now().isoformat(),
                )
            )
            self.assertEquals(200, r.status_code)
            self.assertNotEquals(None, creds['refresh_token'])

            et = ExternalToken.query.filter_by(user=uid)
            self.assertEquals(1, et.count(), 'should only be one token for user')
            et = et.one()
            self.assertEquals(long_lived_fb_token, et.external_token, 'token should be updated')

    @patch('twitter.Api.VerifyCredentials')
    def test_twitter_login_registration(self, verify_credentials):
        twitter_data = TWITTER_DATA.copy()
        twitter_data['id'] = uuid.uuid4().hex
        verify_credentials.return_value = type('U', (object,), {'AsDict': lambda s: twitter_data})()

        with self.app.test_client() as client:
            token_key, token_secret = 'kkkkkkkk', 'sssssss'
            for registered in True, False:
                r = client.post(
                    '/ws/login/external/',
                    headers=[get_client_auth_header()],
                    data=dict(
                        external_system='twitter',
                        external_token=token_key + ':' + token_secret
                    )
                )
                self.assertEquals(200, r.status_code)
                creds = json.loads(r.data)
                self.assertEquals(creds['registered'], registered)

            r = client.get(
                creds['resource_url'],
                headers=[('Authorization', creds['token_type'] + ' ' + creds['access_token'])]
            )
            data = json.loads(r.data)
            self.assertEquals(data['username'], TWITTER_DATA['screen_name'])
            self.assertEquals(data['display_name'], TWITTER_DATA['name'])
            self.assertTrue(data['avatar_thumbnail_url'])

            token = ExternalToken.query.filter_by(user=creds['user_id']).one()
            self.assertEquals(token.external_uid, twitter_data['id'])
            self.assertIn('read', token.permissions)

    @patch('rockpack.mainsite.services.oauth.api.FacebookUser._get_external_data')
    def test_unauthorized_facebook_registration(self, _get_external_data):
        _get_external_data.return_value = {}

        with self.app.test_client() as client:
            facebook_token = uuid.uuid4().hex
            r = client.post(
                '/ws/login/external/',
                headers=[get_client_auth_header()],
                data=dict(
                    external_system='facebook',
                    external_token=facebook_token
                )
            )
            error = json.loads(r.data)
            self.assertEquals(400, r.status_code)
            self.assertEquals('unauthorized_client', error['error'])

    @patch('rockpack.mainsite.services.oauth.api.FacebookUser._get_external_data')
    def test_registration_gender(self, _get_external_data):
        data = FACEBOOK_GRAPH_DATA.copy()
        data['id'] = uuid.uuid4().hex
        data['gender'] = 'm'
        _get_external_data.return_value = data

        with self.app.test_client() as client:
            facebook_token = uuid.uuid4().hex
            r = client.post(
                '/ws/login/external/',
                headers=[get_client_auth_header()],
                data=dict(
                    external_system='facebook',
                    external_token=facebook_token,
                    token_expires='2020-01-01T00:00:00',
                )
            )
            creds = json.loads(r.data)
            self.assertEquals(200, r.status_code)
            self.assertIsNotNone(creds['refresh_token'])
            user_gender = User.query.filter_by(id=creds['user_id']).value('gender')
            self.assertEquals(user_gender, data['gender'])

    @patch('rockpack.mainsite.services.oauth.api.FacebookUser._get_external_data')
    def test_invalid_external_system(self, _get_external_data):
        _get_external_data.return_value = FACEBOOK_GRAPH_DATA
        with self.app.test_client() as client:
            facebook_token = uuid.uuid4().hex
            r = client.post(
                '/ws/login/external/',
                headers=[get_client_auth_header()],
                data=dict(
                    external_system='PantsBake',
                    external_token=facebook_token
                )
            )
            self.assertEquals(400, r.status_code)

    def test_failed_registration(self):
        with self.app.test_client() as client:
            r = client.post(
                '/ws/register/',
                headers=[get_client_auth_header()],
                data=dict(
                    username='',
                    password='barbar',
                    first_name='foo',
                    last_name='bar',
                    date_of_birth='2000-01-01',
                    locale='en-us',
                    email='foo{}@bar.com'.format(uuid.uuid4().hex)
                )
            )
            response = json.loads(r.data)

            self.assertEquals(response['form_errors']['username'][0], 'This field is required.')

    def test_successful_registration(self):

        viewing_user = self.create_test_user().id

        with self.app.test_request_context():
            with self.app.test_client() as client:
                r = client.post(
                    '/ws/register/',
                    headers=[get_client_auth_header()],
                    data=dict(
                        username='foobarbarbar',
                        password='barbar',
                        first_name='foo',
                        last_name='bar',
                        date_of_birth='2000-01-01',
                        locale='en-us',
                        email='foo{}@bar.com'.format(uuid.uuid4().hex)
                    )
                )

        creds = json.loads(r.data)
        self.assertEquals(200, r.status_code)
        self.assertNotEquals(None, creds['refresh_token'])
        self.assertGreaterEqual(Channel.query.filter_by(owner=creds['user_id']).count(), 1,
                                'default user channel should be created')

        self.wait_for_es()

        with self.app.test_client() as client:

            r = client.get(
                '/ws/{}/'.format(creds['user_id']),
                headers=[get_auth_header(viewing_user)]
            )
            self.assertGreaterEqual(json.loads(r.data)['channels']['total'], 1)

            creds = json.loads(r.data)

            r = client.post(
                '/ws/login/',
                headers=[get_client_auth_header()],
                data=dict(
                    grant_type='password',
                    username='foobarbarbar',
                    password='barbar'
                )
            )

            creds = json.loads(r.data)
            self.assertNotEquals(None, creds['refresh_token'])

            r = client.post(
                '/ws/token/',
                headers=[get_client_auth_header()],
                data=dict(
                    refresh_token=creds['refresh_token'],
                    grant_type='refresh_token'
                )
            )

            new_creds = json.loads(r.data)

            self.assertEquals('Bearer', new_creds['token_type'], 'token type should be Bearer')
            self.assertEquals(new_creds['refresh_token'], creds['refresh_token'], 'refresh tokens should be the same')
            self.assertNotEquals(new_creds['access_token'], creds['access_token'],
                                 'old access token should not be the same at the new one')

            # Try and get a refresh token with an invalid token
            r = client.post(
                '/ws/token/',
                headers=[get_client_auth_header()],
                data=dict(refresh_token='7348957nev9o3874nqlvcfh47lmqa')
            )
            self.assertEquals(400, r.status_code)

    def test_naughty_username(self):
        with self.app.test_client() as client:
            for username, status in [('Scunthorpe', 200), ('HorIsACunt', 400)]:
                r = client.post(
                    '/ws/register/',
                    headers=[get_client_auth_header()],
                    data=dict(
                        username=username,
                        password='xxxxxx',
                        first_name='foo',
                        last_name='bar',
                        date_of_birth='2000-01-01',
                        locale='en-us',
                        email='%s@spam.com' % username,
                    )
                )
                self.assertEquals(status, r.status_code, r.data)

    def test_email_addresses(self):
        with self.app.test_client() as client:
            for email, status in [
                    (None, 400),
                    ('', 400),
                    ('foo', 400),
                    ('foo@com', 400),
                    ('foo@.bar.com', 400),
                    ('foo@bar..com', 400),
                    ('foo@bar.com.', 400),
                    ('foo@bar.com', 200)]:
                username = uuid.uuid4().hex
                r = client.post(
                    '/ws/register/',
                    headers=[get_client_auth_header()],
                    data=dict(
                        username=username,
                        password='xxxxxx',
                        first_name='foo',
                        last_name='bar',
                        date_of_birth='1980-01-01',
                        locale='en-us',
                        email=email,
                    )
                )
                self.assertEquals(r.status_code, status,
                                  '%s: %d, %s' % (email, r.status_code, r.data))

    def test_birthdates(self):
        with self.app.test_client() as client:
            for dob, status in [
                    ('1980-01-01', 200),
                    ('1980-31-01', 400),
                    ('1800-01-01', 400),
                    ('2010-01-01', 400),
                    ('2100-01-01', 400)]:
                username = uuid.uuid4().hex
                r = client.post(
                    '/ws/register/',
                    headers=[get_client_auth_header()],
                    data=dict(
                        username=username,
                        password='xxxxxx',
                        first_name='foo',
                        last_name='bar',
                        date_of_birth=dob,
                        locale='en-us',
                        email='%s@spam.com' % username,
                    )
                )
                self.assertEquals(r.status_code, status,
                                  '%s: %d, %s' % (dob, r.status_code, r.data))

    def test_username_availability(self):
        with self.app.test_client() as client:
            self.app.test_request_context().push()
            r = client.post(
                '/ws/register/availability/',
                headers=[get_client_auth_header()],
                data=dict(username=UserData.test_user_a.username),
            )
            self.assertEquals(r.status_code, 200)
            self.assertEquals(json.loads(r.data)['available'], False)

            r = client.post(
                '/ws/register/availability/',
                headers=[get_client_auth_header()],
                data=dict(username='noonehasthisusername'),
            )
            self.assertEquals(r.status_code, 200)
            self.assertEquals(json.loads(r.data)['available'], True)
