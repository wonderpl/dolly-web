import uuid
import json
from test import base
from rockpack.mainsite.services.user.models import User
from rockpack.mainsite.services.video.models import Channel


class ChannelCreateTestCase(base.RockPackTestCase):

    def test_new_channel(self):
        with self.app.test_client() as client:
            user = User(username=uuid.uuid4().hex,
                    first_name='barry',
                    last_name='shitpeas',
                    avatar='',
                    email='em@il.com').save()
            #channel = Channel(title=uuid.uuid4().hex,
            #        description='test channel for user {}'.format(user.id))
            channel_title = uuid.uuid4().hex
            r = client.post('/ws/channels/',
                    data=dict(title=channel_title,
                        description='test channel for user {}'.format(user.id),
                        user=user.id,
                        locale='en-us',
                        category=0))

            print r.data
            self.assertEquals(201, r.status_code)
            new_ch = json.loads(r.data)
            self.assertEquals(1, new_ch['channels']['total'], 'one channel should be returned')
            self.assertEquals(channel_title, new_ch['channels']['items'][0]['title'],
                    'channel titles should match')
