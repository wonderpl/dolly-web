import json
import uuid
from mock import patch
from test import base
from test.fixtures import VideoInstanceData
from test.test_helpers import get_auth_header
from rockpack.mainsite.services.analytics import api


MOCK_VIDEO_JSON = {
    'videos': {
        'items': [
            {
                'date_uploaded': "2014-01-24T16:01:48Z",
                'duration': 20800,
                'embed_code': "9na2xkazr-ZUsHCl3EzTD7XG93GsorB1",
                'name': "Speke tank",
                'resource_url': "http://localhost:5000/ws/analytics/-/9na2xkazr-ZUsHCl3EzTD7XG93GsorB1/",
                'resource_url_weekly': "http://localhost:5000/ws/analytics/-/9na2xkazr-ZUsHCl3EzTD7XG93GsorB1/?start=2014-01-27&end=2014-02-03",
                'thumbnail_url': "http://ak.c.ooyala.com/9na2xkazr-ZUsHCl3EzTD7XG93GsorB1/Ut_HKthATH4eww8X4xMDoxOjBzMTt2bJ"
                }
        ]
    }
}


MOCK_RAW_RESPONSE_JSON = {'items': [{'ad_set_id': None,
             'asset_type': 'video',
             'created_at': '2014-01-24T16:01:48Z',
             'description': None,
             'duration': 20800,
             'embed_code': '9na2xkazr-ZUsHCl3EzTD7XG93GsorB1',
             'external_id': None,
             'hosted_at': '',
             'name': 'Speke tank',
             'original_file_name': 'Speke tank.mov',
             'player_id': 'a6fbe9091fbb4adaa7a28ad75d4d4031',
             'preview_image_url': 'http://ak.c.ooyala.com/9na2xkazr-ZUsHCl3EzTD7XG93GsorB1/Ut_HKthATH4eww8X4xMDoxOjBzMTt2bJ',
             'publishing_rule_id': 'dfa2c304ea0349ffbf7fa54a7a006b76',
             'status': 'live',
             'time_restrictions': None,
             'updated_at': '2014-01-24T16:06:05Z'}]
}


def _mock_video_request(*args, **kwargs):
    return MOCK_RAW_RESPONSE_JSON


class OoyalaAnalytics(base.RockPackTestCase):

    @patch('rockpack.mainsite.services.analytics.api.ooyala_labelid_from_userid')
    @patch('rockpack.mainsite.services.analytics.api._videos_request')
    def test_fetch_all_videos(self, _videos_request, ooyala_labelid_from_userid):
        _videos_request.return_value = MOCK_RAW_RESPONSE_JSON
        ooyala_labelid_from_userid.return_value = 1

        with self.app.test_client() as client:
            self.app.test_request_context().push()
            user = self.create_test_user()

            # create new channel
            r = client.post(
                '/ws/{}/channels/'.format(user.id),
                data=json.dumps(dict(
                    title='test',
                    description='test',
                    category=1,
                    cover='',
                    public=True)
                ),
                content_type='application/json',
                headers=[get_auth_header(user.id)]
            )
            self.assertEquals(r.status_code, 201)
            channel_id = json.loads(r.data)['id']

            # add videos
            client.put(
                '/ws/{}/channels/{}/videos/'.format(user.id, channel_id),
                data=json.dumps([
                    VideoInstanceData.video_instance1.id,
                    VideoInstanceData.video_instance2.id,
                ]),
                content_type='application/json',
                headers=[get_auth_header(user.id)]
            )

            r = client.get(
                '/ws/analytics/{}/'.format(user.id),
                content_type='application/json',
                headers=[get_auth_header(user.id)]
            )

            self.assertEquals(r.status_code, 200)
            self.assertEquals(
                json.loads(r.data)['videos']['items'][0]['embed_code'],
                MOCK_RAW_RESPONSE_JSON['items'][0]['embed_code'])


