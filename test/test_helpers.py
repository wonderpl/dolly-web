import hashlib

from flask import url_for

from test import base

class HeaderTests(base.RockPackTestCase):
    def test_etag(self):
        """ Check existance of ETag in headers
            from whatever endpoing has one """

        with self.app.test_client() as client:
            ctx = self.app.test_request_context()
            ctx.push()
            r = client.get(url_for('CoverArtAPI_api.rockpack_cover_art'))
            self.assertEquals(hashlib.md5(r.data).hexdigest(),
                    r.headers.get('ETag'),
                    'ETag header should match md5\'d content')

    def test_cache_control(self):

        with self.app.test_client() as client:
            ctx = self.app.test_request_context()
            ctx.push()
            r = client.get(url_for('CoverArtAPI_api.rockpack_cover_art'))
            assert r.headers.get('Cache-Control')
