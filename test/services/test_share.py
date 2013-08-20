import re
from urlparse import urlparse
from flask import json
from test import base
from test.test_helpers import get_auth_header
from test.fixtures import ChannelData, VideoInstanceData
from rockpack.mainsite.services.video.models import Channel


class TestShare(base.RockPackTestCase):

    def _share_content(self, userid, object_type, object_id):
        userid = userid or self.create_test_user().id
        with self.app.test_client() as client:
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
        return data

    def test_share_channel(self):
        data = self._share_content(None, 'channel', ChannelData.channel1.id)
        self.assertIn('pack', data['message'])

        # Confirm link redirects to channel
        with self.app.test_client() as client:
            r = client.get(urlparse(data['resource_url']).path)
            self.assertIn(ChannelData.channel1.id, r.headers['Location'])

    def test_share_video(self):
        data = self._share_content(None, 'video_instance', VideoInstanceData.video_instance2.id)

        self.assertEquals(
            'Check out this great video "Primer" on Rockpack',
            data['message_email'],
            'Video title should be in the email message'
        )

        # Confirm link redirects to channel
        with self.app.test_client() as client:
            r = client.get(urlparse(data['resource_url']).path)
            self.assertIn('/%s/' % VideoInstanceData.video_instance2.channel, r.headers['Location'])
            self.assertIn('video=%s' % VideoInstanceData.video_instance2.id, r.headers['Location'])

    def test_passthru_share_params(self):
        data = self._share_content(None, 'video_instance', VideoInstanceData.video_instance2.id)

        self.app.config['SHARE_REDIRECT_PASSTHROUGH_PARAMS'] = ['umts']

        # Confirm link redirects to channel
        with self.app.test_client() as client:
            r = client.get(urlparse(data['resource_url']).path + '?umts=foo')
            self.assertIn('umts=foo', r.headers['Location'])

        self.app.config['SHARE_REDIRECT_PASSTHROUGH_PARAMS'] = None

    def test_share_video_from_search(self):
        self.app.test_request_context().push()
        userid = self.create_test_user().id
        with self.app.test_client() as client:
            r = client.get('/ws/search/videos/', query_string='size=1')
            video = json.loads(r.data)['videos']['items'][0]['id']
        data = self._share_content(userid, 'video_instance', video)

        with self.app.test_client() as client:
            r = client.get(urlparse(data['resource_url']).path)
            self.assertEquals(r.status_code, 302)
            channelid, videoid = re.match(r'.*/([^/]+)/\?.*video=(.+)', r.headers['Location']).groups()

        # try sharing again
        self._share_content(userid, 'video_instance', video)

        # Confirm shared channel & video was from user's favourites
        favourites = Channel.query.filter_by(owner=userid, favourite=True).one()
        self.assertEquals(channelid, favourites.id)
        self.assertEquals([videoid], [v.id for v in favourites.video_instances])
