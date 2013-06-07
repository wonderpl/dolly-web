import re
from urlparse import urlparse
from flask import json
from test import base
from test.test_helpers import get_auth_header
from test.fixtures import ChannelData, VideoInstanceData
from rockpack.mainsite.services.video.models import Channel


class TestShare(base.RockPackTestCase):

    def _share_content(self, object_type, object_id):
        with self.app.test_client() as client:
            userid = self.create_test_user().id
            r = client.post(
                '/ws/share/link/',
                data=json.dumps({
                    'object_type': object_type,
                    'object_id': object_id
                }),
                content_type='application/json',
                headers=[get_auth_header(userid)])

            self.assertEquals(r.status_code, 201, r.data)
            data = json.loads(r.data)
            self.assertIn('/s/', data['resource_url'])
            self.assertEquals(data['resource_url'], r.headers['Location'])
        return userid, data

    def test_share_channel(self):
        userid, data = self._share_content('channel', ChannelData.channel1.id)
        self.assertIn('channel', data['message'])

        # Confirm link redirects to channel
        with self.app.test_client() as client:
            r = client.get(urlparse(data['resource_url']).path)
            self.assertIn(ChannelData.channel1.id, r.headers['Location'])

    def test_share_video(self):
        userid, data = self._share_content('video_instance', VideoInstanceData.video_instance2.id)

        # Confirm link redirects to channel
        with self.app.test_client() as client:
            r = client.get(urlparse(data['resource_url']).path)
            expected_path = '/%s/?video=%s' %\
                (VideoInstanceData.video_instance2.channel, VideoInstanceData.video_instance2.id)
            self.assertIn(expected_path, r.headers['Location'])

    def test_share_video_from_search(self):
        with self.app.test_client() as client:
            r = client.get('/ws/search/videos/', query_string='size=1')
            video = json.loads(r.data)['videos']['items'][0]['id']
        userid, data = self._share_content('video_instance', video)

        with self.app.test_client() as client:
            r = client.get(urlparse(data['resource_url']).path)
            self.assertEquals(r.status_code, 302)
            channelid, videoid = re.match(r'.*/([^/]+)/\?video=(.+)', r.headers['Location']).groups()

        # Confirm shared channel & video was from user's favourites
        favourites = Channel.query.filter_by(owner=userid, favourite=True).one()
        self.assertEquals(channelid, favourites.id)
        self.assertEquals([videoid], [v.id for v in favourites.video_instances])
