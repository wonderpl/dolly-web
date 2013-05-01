import uuid
import json
from urlparse import urlsplit
from test import base
from test.fixtures import RockpackCoverArtData
from test.test_helpers import get_auth_header
from rockpack.mainsite import app
from rockpack.mainsite.services.video import models


class ChannelCreateTestCase(base.RockPackTestCase):

    def test_new_channel(self):
        with self.app.test_client() as client:
            user = self.create_test_user()

            r = client.post('/ws/{}/channels/'.format(user.id),
                    data=json.dumps(dict(title='',
                        description='test channel for user {}'.format(user.id),
                        category=1,
                        cover='',
                        public=False)),
                    content_type='application/json',
                    headers=[get_auth_header(user.id)])

            self.assertEquals(201, r.status_code)
            resource = urlsplit(r.headers['Location']).path
            r = client.get(resource, headers=[get_auth_header(user.id)])
            resp = json.loads(r.data)
            new_ch = models.Channel.query.filter(
                models.Channel.title.like(app.config['UNTITLED_CHANNEL'] + '%')).one()
            self.assertEquals(False, resp['public'], 'channel should be private')

            # test channel update
            new_description = 'this is a new description!'
            r = client.put(resource,
                    data=json.dumps(dict(title='a new channel title',
                        description=new_description,
                    category=3,
                    cover=RockpackCoverArtData.comic_cover.cover,
                    public=False)),
                    content_type='application/json',
                    headers=[get_auth_header(user.id)])
            self.assertEquals(200, r.status_code)

            r = client.get(resource, headers=[get_auth_header(user.id)])
            updated_ch = json.loads(r.data)
            self.assertEquals(new_description, updated_ch['description'],
                    'channel descriptions should match')
            self.assertNotEquals('', updated_ch['cover_background_url'],
                    'channel cover should not be blank')
            channel = models.Channel.query.get(new_ch.id)
            self.assertEquals(channel.category, 3)

            # check that the dup-title error isnt triggered when updating
            # but not changing the title
            # also check stripping of returns (200 chars not including break)
            new_description = 'this is a new description!'
            new_description = "hjdk adhaj dsjakhkdsjf yhsdjhf sdjhfksdkfjhsdfsjdfjsdfh sdhf sdjkhf jhsjkhsf sdjhkf sdjkhsdfjkhfsdh\n\rhjdk adhaj dsjakhkdsjf yhsdjhf sdjhfksdkfjhsdfsjdfjsdfh sdhf sdjkhf jhsjkhsf sdjhkf sdjkhsdfjkhfsdh"
            r = client.put(resource,
                    data=json.dumps(dict(title='',
                        description=new_description,
                    category=3,
                    cover=RockpackCoverArtData.comic_cover.cover,
                    public=False)),
                    content_type='application/json',
                    headers=[get_auth_header(user.id)])
            self.assertEquals(200, r.status_code)

            # check description limit (201 chars below)
            new_description = "ihjdk adhaj dsjakhkdsjf yhsdjhf sdjhfksdkfjhsdfsjdfjsdfh sdhf sdjkhf jhsjkhsf sdjhkf sdjkhsdfjkhfsdh\n\rhjdk adhaj dsjakhkdsjf yhsdjhf sdjhfksdkfjhsdfsjdfjsdfh sdhf sdjkhf jhsjkhsf sdjhkf sdjkhsdfjkhfsdh"
            r = client.put(resource,
                    data=json.dumps(dict(title='',
                        description=new_description,
                    category=3,
                    cover=RockpackCoverArtData.comic_cover.cover,
                    public=False)),
                    content_type='application/json',
                    headers=[get_auth_header(user.id)])
            self.assertEquals(400, r.status_code)

            # test public toggle
            r = client.put(resource + 'public/',
                    data=json.dumps(False),
                    content_type='application/json',
                    headers=[get_auth_header(user.id)])
            data = json.loads(r.data)
            self.assertEquals(data, False)

            r = client.put(resource + 'public/',
                    data=json.dumps(True),
                    content_type='application/json',
                    headers=[get_auth_header(user.id)])
            data = json.loads(r.data)
            self.assertEquals(data, True)

    def test_failed_channel_create(self):
        with self.app.test_client() as client:
            user = self.create_test_user()

            channel_title = uuid.uuid4().hex
            r = client.post('/ws/{}/channels/'.format(user.id),
                    data=dict(title=channel_title),
                    headers=[get_auth_header(user.id)])

            self.assertEquals(400, r.status_code)
            errors = json.loads(r.data)['form_errors']
            self.assertEquals({
                "category": ["This field is required, but can be an empty string."],
                "public": ["This field is required, but can be an empty string."],
                "description": ["This field is required, but can be an empty string."],
                "cover":["This field is required, but can be an empty string."]},
                errors)
