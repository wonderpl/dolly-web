import uuid
import json
from urlparse import urlsplit
from test import base
from test.fixtures import RockpackCoverArtData
from test.test_helpers import get_auth_header


class ChannelCreateTestCase(base.RockPackTestCase):

    def test_new_channel(self):
        with self.app.test_client() as client:
            user = self.create_test_user()

            channel_title = uuid.uuid4().hex
            r = client.post('/ws/{}/channels/'.format(user.id),
                    data=dict(title=channel_title,
                        description='test channel for user {}'.format(user.id),
                        owner=user.id,
                        locale='en-us',
                        category=0,
                        cover='',
                        visible=False),
                    headers=[get_auth_header(user.id)])

            self.assertEquals(201, r.status_code)
            resource = urlsplit(r.headers['Location']).path
            r = client.get(resource, headers=[get_auth_header(user.id)])
            new_ch = json.loads(r.data)
            self.assertEquals(channel_title, new_ch['title'],
                    'channel titles should match')
            self.assertEquals('', new_ch['cover_background_url'],
                    'channel cover should be blank')

            # test channel update
            new_description = 'this is a new description!'
            r = client.put(resource,
                    data=dict(title='',
                        description=new_description,
                    owner=user.id,
                    category=1,
                    locale='',
                    cover=RockpackCoverArtData.comic_cover.cover,
                    visible=False),
                    headers=[get_auth_header(user.id)])
            self.assertEquals(204, r.status_code)

            r = client.get(resource, headers=[get_auth_header(user.id)])
            updated_ch = json.loads(r.data)
            self.assertEquals(new_description, updated_ch['description'],
                    'channel descriptions should match')
            self.assertNotEquals('', updated_ch['cover_background_url'],
                    'channel cover should not be blank')

    def test_failed_channel_create(self):
        with self.app.test_client() as client:
            user = self.create_test_user()

            channel_title = uuid.uuid4().hex
            r = client.post('/ws/{}/channels/'.format(user.id),
                    data=dict(title=channel_title,
                        owner=user.id,
                        locale='en-us'),
                    headers=[get_auth_header(user.id)])

            self.assertEquals(400, r.status_code)
            errors = json.loads(r.data)['form_errors']
            self.assertEquals({
                "category": ["This field is required, but can be an empty string."],
                "description": ["This field is required, but can be an empty string."],
                "cover":["This field is required, but can be an empty string."]},
                errors)
