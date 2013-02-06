import json

from rockpack.mainsite.auth.models import User

from test import base
from test.assets import AVATAR_IMG_PATH

from test.fixtures import UserData

class CoverArtTestCase(base.RockPackTestCase):

    def test_rockpack_cover(self):
        with self.app.test_client() as client:
            r = client.get('/ws/cover_art/')
            j = json.loads(r.data)
            self.assertEquals(j['cover_art'][0]['id'], 1, 'ids should match')
            assert j['cover_art'][0]['background_url'].startswith(
                     '{0}/images/channel/background/'.format(self.app.config['IMAGE_CDN']))
            assert j['cover_art'][0]['carousel_url'].startswith(
                     '{0}/images/channel/carousel/'.format(self.app.config['IMAGE_CDN']))


class UserCoverArtTestCase(base.RockPackTestCase):

    def test_upload_cover_art(self):
        with self.app.test_client() as client:
            user = User.query.filter(
                User.username == UserData.test_user_a.username).first()

            r = client.post('/ws/{}/cover_art/'.format(user.id), data={
                'file': (AVATAR_IMG_PATH, 'img.jpg')})

            self.assertEquals(r.status_code, 201)

            j = json.loads(r.data)
            assert j['cover_art'][0]['background_url'].startswith(
                     '{0}/images/channel/background/'.format(self.app.config['IMAGE_CDN']))
