import uuid
import json
from test import base
from rockpack.mainsite.services.user.models import User


class ChannelCreateTestCase(base.RockPackTestCase):

    def test_new_channel(self):
        with self.app.test_client() as client:
            user = User(username=uuid.uuid4().hex,
                    first_name='barry',
                    last_name='shitpeas',
                    avatar='',
                    email='em@il.com').save()

            channel_title = uuid.uuid4().hex
            r = client.post('/ws/channels/',
                    data=dict(title=channel_title,
                        description='test channel for user {}'.format(user.id),
                        owner=user.id,
                        locale='en-us',
                        category=0))

            self.assertEquals(201, r.status_code)
            new_ch = json.loads(r.data)
            self.assertEquals(1, new_ch['channels']['total'], 'one channel should be returned')
            self.assertEquals(channel_title, new_ch['channels']['items'][0]['title'],
                    'channel titles should match')

            # test channel update
            new_description = 'this is a new description!'
            r = client.put('/ws/channels/{}/'.format(new_ch['channels']['items'][0]['id']),
                    data=dict(title='',
                        description=new_description,
                    owner=user.id,
                    category='',
                    locale=''))
            updated_ch = json.loads(r.data)

            self.assertEquals(200, r.status_code)
            self.assertEquals(new_description, updated_ch['channels']['items'][0]['description'],
                    'channel descriptions should match')

    def test_failed_channel_create(self):
        with self.app.test_client() as client:
            user = User(username=uuid.uuid4().hex,
                    first_name='barry',
                    last_name='shitpeas',
                    avatar='',
                    email='em@il.com').save()

            channel_title = uuid.uuid4().hex
            r = client.post('/ws/channels/',
                    data=dict(title=channel_title,
                        owner=user.id,
                        locale='en-us'))

            self.assertEquals(400, r.status_code)
            errors = json.loads(r.data)['errors']
            self.assertEquals({
                "category": ["This field is required."],
                "description": ["This field is required."]},
                errors)
