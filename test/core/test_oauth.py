from datetime import datetime, timedelta
from mock import patch, PropertyMock
import urllib
import urlparse
import flask
from flask import request

from test.base import RockPackTestCase

from rockpack.mainsite.core.oauth.provider import (
        RockpackAuthorisationProvider, RockpackResourceProvider,
        TokenMapper)


class DummyEngine(object):

    redirect_uri = '/this/is/a/redirect/' # provider by the client
    secret = 'sssssssssssshhhhhh' # generated by provider
    client_id = 'this_is_a_client_id'

    def find(self, client_id):
        return self if self.client_id == client_id else None


class DummyAuthStore(TokenMapper):

    def __init__(self):
        self._dict = {}

    def _get_token(self, key):
        return self._dict.get(key, ())

    def _set_token(self, key, data):
        self._dict[key] = data
        print 'set key', key, 'with', data

    def _delete_token(self, key):
        try:
            del self._dict[key]
        except KeyError:
            print 'no key', key, 'present'
        else:
            print 'dropped key', key

    def set_auth_token(self, key, expires, data):
        self._set_token(key, (datetime.utcnow() + timedelta(seconds=expires), data,))

    def get_auth_token(self, key):
        return self._get_token(key)

    def delete_auth_token(self, key):
        self._delete_token(key)

    def set_access_refresh_pair(self, key, access_key, refresh_key):
        self._set_token(key, (access_key, refresh_key,))

    def delete_access_refresh_pair(self, key):
        self._delete_token(key)


# XXX: Temporarily disabled: throwing :
#  File "/usr/lib/python2.7/site-packages/flask/app.py", line 56, in wrapper_func
#    raise AssertionError('A setup function was called after the '
class _TestOauthProvider(RockPackTestCase):

    def setUp(self):
        super(_TestOauthProvider, self).setUp()

        self.test_client_id = 'some_client_id'
        self.dummy_engine = DummyEngine()
        self.dummy_auth_store = DummyAuthStore()

        # Mock out a valid user session
        patcher = patch('flask.session', new_callable=PropertyMock)
        self.addCleanup(patcher.stop)
        self.mock_session = patcher.start()

        type(self.mock_session).user = 'this_user'
        type(self.mock_session).user_id = 'this_user_id'

        from rockpack.mainsite import app

        @app.route('/test/oauth2/auth', methods=('GET',))
        def auth_code():
            provider = RockpackAuthorisationProvider(self.dummy_engine, self.dummy_auth_store)

            response = provider.get_authorization_code_from_uri(request.url)

            flask_res = flask.make_response(response.text, response.status_code)
            for k, v, in response.headers.iteritems():
                flask_res.headers[k] = v
            return flask_res

        @app.route('/test/oauth2/token', methods=('POST',))
        def token():
            provider = RockpackAuthorisationProvider(self.dummy_engine, self.dummy_auth_store)

            data = {k: v for k, v in request.form.iteritems()}

            response = provider.get_token_from_post_data(data)

            flask_res = flask.make_response(response.text, response.status_code)
            for k, v in response.headers.iteritems():
                flask_res.headers[k] = v
            return flask_res

        @app.route('/test/some/protected/resource', methods=('GET',))
        def protected_resource():
            provider = RockpackResourceProvider(self.dummy_auth_store)

            auth = provider.get_authorization()
            if not auth.is_valid:
                flask.abort(400)

            # auth.client_id

            return flask.make_response('Wee')

    def _call_auth(self, client, response_type='code', client_id=DummyEngine.client_id,
            redirect_uri=DummyEngine.redirect_uri, rockpack_id='fv7j4uewhnr7rt34yklfyaiojkl'):
        return client.get('/test/oauth2/auth?{}'.format(
                urllib.urlencode({'response_type': response_type,
                    'client_id': client_id,
                    'redirect_uri': redirect_uri,
                    'rockpack_id': rockpack_id})
                ))

    def _call_token(self, client, code, grant_type='authorization_code', client_id=DummyEngine.client_id,
            client_secret=DummyEngine.secret, redirect_uri=DummyEngine.redirect_uri):
        return client.post('/test/oauth2/token',
                data={'code': code,
                    'grant_type': grant_type,
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'redirect_uri': redirect_uri})

    def test_auth_flow(self):
        with self.app.test_client() as client:
            r = self._call_auth(client)

            self.assertEquals(302, r.status_code, 'response status should be 302')
            redirect_data = dict(urlparse.parse_qsl(urlparse.urlparse(r.headers.get('Location')).query, True))
            found = [v for v in self.dummy_auth_store._dict.keys() if v.find(redirect_data['code']) != -1]
            assert found

            code = redirect_data.get('code')

            # Returns:
            # code=hw87y9vtwnq7834oywv879ymo8l435sd
            # &rockpack_id=fv7j4uewhnr7rt34yklfyaiojkl

            # simulate backend calls - THIS IS NOT WHAT BROWSER SENDS
            # code is normally sent to server app and they make the
            # follow call to the api
            r = self._call_token(client, code)

            #assert 'access_token' in r.data
            #assert 'refresh_token' in r.data

            #response_data = json.loads(r.data)

            # Returns:
            # {"access_token": "78435n0q2vpo934po8um4j867qnpo9l345i",
            # "refresh_token": "785vo6whkv7ym4t7g8m4n58sib546w5sye"}

            # Now that we have an access_token ...

            #headers = [('Authorization', ' '.join(['Bearer', response_data['access_token']]))]
            #r = client.get('/test/some/protected/resource', headers=headers) # access token as bearer header

            #self.assertEquals(200, r.status_code)

    def test_failed_auth_request(self):
        with self.app.test_client() as client:
            r = client.get('/test/oauth2/auth?{}'.format(
                    urllib.urlencode({'response_type': 'code',
                        'client_id': 'some_non_existant_client_id',
                        'redirect_uri': DummyEngine.redirect_uri,
                        'rockpack_id': 'fv7j4uewhnr7rt34yklfyaiojkl'})))

            self.assertEquals(400, r.status_code)

    def test_bad_token(self):
        with self.app.test_client() as client:
            r = self._call_auth(client)
            redirect_data = dict(urlparse.parse_qsl(urlparse.urlparse(r.headers.get('Location')).query, True))
            code = redirect_data.get('code')

            r = self._call_token(client, code)

            headers = [('Authorization', ' '.join(['Bearer', 'this_is_a_bad_token']))]
            r = client.get('/test/some/protected/resource', headers=headers)
            #self.assertEquals(400, r.status_code)