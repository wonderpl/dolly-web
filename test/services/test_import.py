from mock import patch
from cStringIO import StringIO

from test import base
from test.fixtures import UserData
from test.assets import AVATAR_IMG_PATH

from rockpack.mainsite.admin.import_views import ImportView
from rockpack.mainsite.services.video.models import Video, VideoInstance, Channel
from rockpack.mainsite.auth.models import User


class ImportFromYoutubeTestCase(base.RockPackTestCase):

    data_video = {'source': 1,
            'type': 'video',
            'id': 'oruNL3TXmlc',
            'locale': 'en-us',
            'category': 1,
            'commit': 1}

    data_video_1 = {'source': 1,
            'type': 'video',
            'id': 'FNQowwwwYa0',
            'locale': 'en-us',
            'category': 1,
            'commit': 1}

    data_user = {'username': 'test_user_flarnflagger',
            'first_name': 'flarn',
            'last_name': 'flagger',
            'email': 'flarn@flagger.com'}

    data_channel = {'channel': '_new:test_channel',
            'channel_description': 'test description'}

    def tearDown(self):
        Video.query.filter_by(source_videoid=self.data_video['id']).delete()

    def test_import_with_new_user(self):
        # Override admin login
        with patch.object(ImportView, 'is_authenticated') as mock_prop:
            mock_prop.return_value = True
            with self.app.test_client() as client:
                data = self.data_video.copy()
                data.update(self.data_user.copy())
                data.update({'avatar': (StringIO(AVATAR_IMG_PATH), 'avatar.jpg',)})

                r = client.post('/admin/import/', data=data)

                self.assertEquals(r.status_code, 302)
                assert User.query.filter_by(username=self.data_user['username'])
                self.assertEquals(1,
                        Video.query.filter_by(source_videoid=self.data_video['id']).count())

    def test_failed_with_user_and_missing_category(self):
        with patch.object(ImportView, 'is_authenticated') as mock_prop:
            mock_prop.return_value = True
            with self.app.test_client() as client:
                data = self.data_video.copy()
                data.update(self.data_user.copy())
                data.update({'avatar': (StringIO(AVATAR_IMG_PATH), 'avatar.jpg',)})
                del data['category']
                r = client.post('/admin/import/', data=data)

                self.assertEquals(r.status_code, 200)
                self.assertEquals(0,
                        Video.query.filter_by(source_videoid=self.data_video['id']).count())

    def test_import_only(self):
        with patch.object(ImportView, 'is_authenticated') as mock_prop:
            mock_prop.return_value = True
            with self.app.test_client() as client:
                data = self.data_video.copy()
                data.update({'user':
                    User.query.filter_by(username=UserData.test_user_a.username).first()})

                r = client.post('/admin/import/', data=data)

                self.assertEquals(r.status_code, 302)
                self.assertEquals(1,
                        Video.query.filter_by(source_videoid=self.data_video['id']).count())

    def test_import_with_channel(self):
        with patch.object(ImportView, 'is_authenticated') as mock_prop:
            mock_prop.return_value = True
            with self.app.test_client() as client:
                data = self.data_video.copy()
                data.update({'user':
                    User.query.filter_by(username=UserData.test_user_a.username).first().id})
                data.update(self.data_channel.copy())

                r = client.post('/admin/import/', data=data)
                self.assertEquals(r.status_code, 302)
                video = Video.query.filter_by(source_videoid=self.data_video['id']).one()

                channels = Channel.query.filter_by(title=data['channel'].split(':', 1)[1])
                channel = channels.one()
                self.assertEquals(1, channels.count())
                self.assertEquals(data['channel_description'], channel.description)

                assert VideoInstance.query.filter_by(channel=channel.id, video=video.id).one()

                # add another video to existing channel

                data = self.data_video_1.copy()
                data.update({'user':
                    User.query.filter_by(username=UserData.test_user_a.username).first().id})
                data['channel'] = channel.id

                r = client.post('/admin/import/', data=data)

                video = Video.query.filter_by(source_videoid=self.data_video_1['id']).one()
                self.assertEquals(2, VideoInstance.query.filter_by(channel=channel.id).count())
