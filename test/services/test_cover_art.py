import json
from flask import url_for
from rockpack.mainsite.services.user.models import User
from test import base
from test.assets import AVATAR_IMG_PATH
from test.fixtures import UserData
from test.test_helpers import get_auth_header


class CoverArtTestCase(base.RockPackTestCase):

    def test_rockpack_cover(self):
        with self.app.test_client() as client:
            ctx = self.app.test_request_context()
            ctx.push()
            r = client.get(url_for('coverartws.rockpack_cover_art'))
            j = json.loads(r.data)
            assert j['cover_art']['items'][0]['thumbnail_url'].startswith(
                '{0}/images/channel/thumbnail_medium/'.format(self.app.config['IMAGE_CDN']))


class UserCoverArtTestCase(base.RockPackTestCase):

    def test_upload_cover_art(self):
        with self.app.test_client() as client:
            user = User.query.filter(
                User.username == UserData.test_user_a.username).first()

            r = client.post('/ws/{}/cover_art/'.format(user.id),
                            data={'image': (AVATAR_IMG_PATH, 'img.jpg')},
                            headers=[get_auth_header(user.id)])

            self.assertEquals(r.status_code, 201)

            j = json.loads(r.data)
            assert j['thumbnail_url'].startswith(
                '{0}/images/channel/thumbnail_medium/'.format(self.app.config['IMAGE_CDN']))

    def test_cover_art_has_ref(self):
        """ All images are resized and coverted to JPEG format.

            `instance`.cover should return a filename with the original
            file extension (e.g. '.png') and NOT '.jpg' (unless, of course,
            it was JPEG to begin with). """

        with self.app.test_client() as client:
            user = User.query.filter(
                User.username == UserData.test_user_a.username).first()

            r = client.post('/ws/{}/cover_art/'.format(user.id),
                            data={'image': (AVATAR_IMG_PATH, 'img.png')},
                            headers=[get_auth_header(user.id)])

            self.assertEquals(r.status_code, 201)

            j = json.loads(r.data)
            assert j['thumbnail_url'].startswith(
                '{0}/images/channel/thumbnail_medium/'.format(self.app.config['IMAGE_CDN']))

            cover_ref = j['cover_ref']
            assert cover_ref.endswith('.png')

            assert j['thumbnail_url'].endswith('.jpg')

    def test_failed_upload(self):
        with self.app.test_client() as client:
            user = User.query.filter(
                User.username == UserData.test_user_a.username).first()

            r = client.post('/ws/{}/cover_art/'.format(user.id),
                            data={},
                            headers=[get_auth_header(user.id)])

            self.assertEquals(r.status_code, 400)
