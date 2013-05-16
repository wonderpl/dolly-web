import uuid
import json
from datetime import datetime
from urlparse import urlsplit
from test import base
from test.fixtures import RockpackCoverArtData, VideoInstanceData
from test.test_helpers import get_auth_header
from rockpack.mainsite import app
from rockpack.mainsite.services.video import models


class ChannelPopularity(base.RockPackTestCase):
    def test_channel_order(self):
        with self.app.test_client() as client:
            user = self.create_test_user()

            r = client.get(
                '/ws/channels/',
                content_type='application/json',
                headers=[get_auth_header(user.id)]
            )

            data = json.loads(r.data)
            #self.assertEquals(data['channels']['items'][0]['title'], 'channel #6')


class ChannelCreateTestCase(base.RockPackTestCase):

    def test_new_channel(self):
        with self.app.test_client() as client:
            user = self.create_test_user()
            user2_id = self.create_test_user().id

            r = client.post(
                '/ws/{}/channels/'.format(user.id),
                data=json.dumps(dict(
                    title='',
                    description='test channel for user {}'.format(user.id),
                    category=1,
                    cover='',
                    public=False)
                ),
                content_type='application/json',
                headers=[get_auth_header(user.id)]
            )

            self.assertEquals(201, r.status_code)
            resource = urlsplit(r.headers['Location']).path
            r = client.get(resource, headers=[get_auth_header(user.id)])
            resp = json.loads(r.data)
            new_ch = models.Channel.query.filter(
                models.Channel.title.like(app.config['UNTITLED_CHANNEL'] + '%')).one()
            self.assertEquals(False, resp['public'], 'channel should be private')

            # Visible to owner
            r = client.get(
                '/ws/{}/channels/{}/'.format(user.id, new_ch.id),
                content_type='application/json',
                headers=[get_auth_header(user.id)]
            )
            self.assertEquals('200 OK', r.status)

            # Invisible to public
            r = client.get(
                '/ws/{}/channels/{}/'.format(user.id, new_ch.id),
                content_type='application/json',
                headers=[get_auth_header(user2_id)]
            )
            self.assertEquals('404 NOT FOUND', r.status)

            # test channel update
            new_title = 'a new channel title'
            new_description = 'this is a new description!'
            r = client.put(
                resource,
                data=json.dumps(dict(
                    title=new_title,
                    description=new_description,
                    category=3,
                    cover=RockpackCoverArtData.comic_cover.cover,
                    public=False)
                ),
                content_type='application/json',
                headers=[get_auth_header(user.id)]
            )
            self.assertEquals(200, r.status_code)

            resource = urlsplit(r.headers['Location']).path

            r = client.get(resource, headers=[get_auth_header(user.id)])
            updated_ch = json.loads(r.data)
            self.assertEquals(new_title, updated_ch['title'], 'channel titles should match')
            self.assertNotEquals('', updated_ch['cover']['thumbnail_url'],
                                 'channel cover should not be blank')
            channel = models.Channel.query.get(new_ch.id)
            self.assertEquals(channel.category, 3)

            # check that the dup-title error isnt triggered when updating
            # but not changing the title
            # also check stripping of returns (200 chars not including break)
            new_description = "hjdk adhaj dsjakhkdsjf yhsdjhf sdjhfksdkfjhsdfsjdfjsdfh sdhf sdjkhf jhsjkhsf sdjhkf sdjkhsdfjkhfsdh\n\rhjdk adhaj dsjakhkdsjf yhsdjhf sdjhfksdkfjhsdfsjdfjsdfh sdhf sdjkhf jhsjkhsf sdjhkf sdjkhsdfjkhfsdh"
            r = client.put(
                resource,
                data=json.dumps(dict(
                    title=new_title,
                    description=new_description,
                    category=3,
                    cover=RockpackCoverArtData.comic_cover.cover,
                    public=False)
                ),
                content_type='application/json',
                headers=[get_auth_header(user.id)]
            )
            self.assertEquals(200, r.status_code)


            # test duplicate title
            r = client.post(
                '/ws/{}/channels/'.format(user.id),
                data=json.dumps(dict(
                    title=new_title,
                    description='test channel for user {}'.format(user.id),
                    category=1,
                    cover='',
                    public=False)
                ),
                content_type='application/json',
                headers=[get_auth_header(user.id)]
            )

            self.assertEquals(400, r.status_code)
            self.assertEquals('Duplicate title.', json.loads(r.data)['form_errors']['title'][0])

            # check description limit (201 chars below)
            new_description = "ihjdk adhaj dsjakhkdsjf yhsdjhf sdjhfksdkfjhsdfsjdfjsdfh sdhf sdjkhf jhsjkhsf sdjhkf sdjkhsdfjkhfsdh\n\rhjdk adhaj dsjakhkdsjf yhsdjhf sdjhfksdkfjhsdfsjdfjsdfh sdhf sdjkhf jhsjkhsf sdjhkf sdjkhsdfjkhfsdh"
            r = client.put(
                resource,
                data=json.dumps(dict(
                    title='',
                    description=new_description,
                    category=3,
                    cover=RockpackCoverArtData.comic_cover.cover,
                    public=False)
                ),
                content_type='application/json',
                headers=[get_auth_header(user.id)]
            )
            self.assertEquals(400, r.status_code)

            # test public toggle
            r = client.put(
                resource + 'public/',
                data=json.dumps(False),
                content_type='application/json',
                headers=[get_auth_header(user.id)]
            )
            data = json.loads(r.data)
            self.assertEquals(data, False)
            self.assertEquals(models.Channel.query.get(new_ch.id).public, False)

            r = client.put(
                resource + 'public/',
                data=json.dumps(True),
                content_type='application/json',
                headers=[get_auth_header(user.id)]
            )
            data = json.loads(r.data)
            self.assertEquals(data, False)
            self.assertEquals(
                models.Channel.query.get(new_ch.id).public,
                False,
                'channel should be private without videos even if detail-complete')

            r = client.post(
                resource + 'videos/',
                data=json.dumps([VideoInstanceData.video_instance1.id]),
                content_type='application/json',
                headers=[get_auth_header(user.id)]
            )
            self.assertEquals(r.status_code, 204)
            self.assertEquals(
                models.Channel.query.get(new_ch.id).public,
                True,
                'channel should be public if adding a video and detail-complete')

            r = client.put(
                resource + 'public/',
                data=json.dumps(False),
                content_type='application/json',
                headers=[get_auth_header(user.id)]
            )
            data = json.loads(r.data)
            self.assertEquals(data, False)
            self.assertEquals(
                models.Channel.query.get(new_ch.id).public,
                False,
                'channel should not be public if privacy is toggled false')

    def test_failed_channel_create(self):
        with self.app.test_client() as client:
            user = self.create_test_user()

            channel_title = uuid.uuid4().hex
            r = client.post(
                '/ws/{}/channels/'.format(user.id),
                data=dict(title=channel_title),
                headers=[get_auth_header(user.id)]
            )

            self.assertEquals(400, r.status_code)
            errors = json.loads(r.data)['form_errors']
            self.assertEquals({
                "category": ["This field is required, but can be an empty string."],
                "public": ["This field is required, but can be an empty string."],
                "description": ["This field is required, but can be an empty string."],
                "cover": ["This field is required, but can be an empty string."]},
                errors)

    def test_channel_order(self):
        # Hack to ensure channels have ordered date_updated values
        updated_default = models.Channel.__table__.columns['date_updated'].onupdate
        updated_default_bak = updated_default.arg, updated_default.is_clause_element
        updated_default.is_clause_element = False

        with self.app.test_client() as client:
            user = self.create_test_user()
            user2_id = self.create_test_user().id

            c1 = None
            for i in range(3):
                updated_default.arg = datetime(2013, 1, i + 1)
                r = client.post(
                    '/ws/{}/channels/'.format(user.id),
                    data=json.dumps(dict(
                        title=str(i),
                        description='',
                        category='1',
                        cover=RockpackCoverArtData.comic_cover.cover,
                        public=True,
                    )),
                    content_type='application/json',
                    headers=[get_auth_header(user.id)]
                )
                self.assertEquals(201, r.status_code, r.data)
                if i == 1:
                    c1 = json.loads(r.data)['id']
                r = client.post(
                    urlsplit(r.headers['Location']).path + 'videos/',
                    data=json.dumps([VideoInstanceData.video_instance1.id]),
                    content_type='application/json',
                    headers=[get_auth_header(user.id)]
                )
                self.assertEquals(r.status_code, 204)

            updated_default.arg = datetime(2013, 2, 1)
            r = client.put(
                '/ws/{}/channels/{}/'.format(user.id, c1),
                data=json.dumps(dict(
                    title='updated',
                    description='x',
                    category='1',
                    cover=RockpackCoverArtData.comic_cover.cover,
                    public=True,
                )),
                content_type='application/json',
                headers=[get_auth_header(user.id)]
            )
            self.assertEquals(200, r.status_code, r.data)

            for user_id in user.id, user2_id:
                r = client.get('/ws/{}/'.format(user.id), headers=[get_auth_header(user_id)])
                self.assertEquals(200, r.status_code)
                channels = json.loads(r.data)['channels']
                self.assertEquals(channels['total'], 4)
                titles = [c['title'] for c in channels['items']]
                self.assertEquals(titles, ['Favourites', 'updated', '2', '0'])

        # restore date_updated onupdate default
        updated_default.arg, updated_default.is_clause_element = updated_default_bak

    def test_channel_editable(self):
        with self.app.test_client() as client:
            user = self.create_test_user()
            r = client.post(
                '/ws/{}/channels/'.format(user.id),
                data=json.dumps(dict(title='x', category='', description='', cover='', public='')),
                content_type='application/json',
                headers=[get_auth_header(user.id)]
            )
            self.assertEquals(201, r.status_code, r.data)

            r = client.get('/ws/{}/'.format(user.id), headers=[get_auth_header(user.id)])
            channels = json.loads(r.data)['channels']['items']
            favourites_url = [c['resource_url'] for c in channels if c.get('favourites')][0]
            normal_url = [c['resource_url'] for c in channels if not c.get('favourites')][0]

            for url, code in (favourites_url, 400), (normal_url, 200):
                path = urlsplit(url).path
                r = client.put(
                    path,
                    data=json.dumps(dict(title='test', category='', description='', cover='', public='')),
                    content_type='application/json',
                    headers=[get_auth_header(user.id)]
                )
                self.assertEquals(code, r.status_code, r.data)
                r = client.put(
                    path + 'public/',
                    data='false',
                    content_type='application/json',
                    headers=[get_auth_header(user.id)]
                )
                self.assertEquals(code, r.status_code, r.data)
                r = client.delete(path,
                                  content_type='application/json',
                                  headers=[get_auth_header(user.id)])
                self.assertEquals(204 if code == 200 else code, r.status_code, r.data)
