import hashlib
import base64
from flask import url_for
from rockpack.mainsite import app
from test import base


class MockS3Uploader(object):
    files = {}

    def put_from_filename(self, filename, key, headers=None):
        self.files[key] = open(filename).read()

    def put_from_file(self, file, key, headers=None):
        self.files[key] = file.read()

    def exists(self, key):
        return key in self.files


def install_mocks():
    from rockpack.mainsite.core import s3
    s3.S3Uploader = MockS3Uploader


def get_auth_header(userid):
    from rockpack.mainsite.core.token import create_access_token
    return 'Authorization', 'Bearer %s' % create_access_token(userid, '', 60)


def get_client_auth_header():
    credentials = base64.b64encode(app.config['ROCKPACK_APP_CLIENT_ID'] + ':')
    return 'Authorization', 'Basic %s' % credentials


class HeaderTests(base.RockPackTestCase):
    def test_etag(self):
        """ Check existance of ETag in headers
            from whatever endpoing has one """

        with self.app.test_client() as client:
            ctx = self.app.test_request_context()
            ctx.push()
            r = client.get(url_for('coverartws.rockpack_cover_art'))
            self.assertEquals(
                '"%s"' % hashlib.md5(r.data).hexdigest(),
                r.headers.get('ETag'),
                'ETag header should match md5\'d content')

    def test_cache_control(self):

        with self.app.test_client() as client:
            ctx = self.app.test_request_context()
            ctx.push()
            r = client.get(url_for('coverartws.rockpack_cover_art'))
            assert r.headers.get('Cache-Control')
