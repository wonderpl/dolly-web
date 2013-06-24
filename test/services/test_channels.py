import uuid
import time
import json
from datetime import datetime, timedelta
from urlparse import urlsplit
from test import base
from test.fixtures import RockpackCoverArtData, VideoInstanceData, VideoData
from test.test_helpers import get_auth_header
from rockpack.mainsite import app
from rockpack.mainsite.services.video.commands import set_channel_view_count
from rockpack.mainsite.core.es import use_elasticsearch
from rockpack.mainsite.core.es.api import ChannelSearch
from rockpack.mainsite.services.video import models
from rockpack.mainsite.services.user.models import UserActivity


class ChannelViewCountPopulation(base.RockPackTestCase):

    def test_populate(self):
        """ Populate the view count on channel locale meta """
        with self.app.test_client() as client:
            self.app.test_request_context().push()
            user = self.create_test_user()
            user2_id = self.create_test_user().id
            user3_id = self.create_test_user().id
            user4_id = self.create_test_user().id

            begin = datetime.now() - timedelta(hours=2)

            # test duplicate title
            r = client.post(
                '/ws/{}/channels/'.format(user.id),
                data=json.dumps(dict(
                    title='new title',
                    description='test channel for user {}'.format(user.id),
                    category=1,
                    cover=RockpackCoverArtData.comic_cover.cover,
                    public=True)
                ),
                content_type='application/json',
                headers=[get_auth_header(user.id)]
            )
            channel_id = json.loads(r.data)['id']
            this_locale = 'en-us'

            models.ChannelLocaleMeta(
                    channel=channel_id,
                    locale=this_locale,
                    date_added=datetime.now()).save()

            video_instance = models.VideoInstance(
                    channel=channel_id,
                    video=VideoData.video1.id).save()

            UserActivity(
                user=user2_id,
                action='view',
                date_actioned=datetime.now(),
                object_type='channel',
                object_id=channel_id,
                locale=this_locale).save()


            UserActivity(
                user=user3_id,
                action='view',
                date_actioned=datetime.now(),
                object_type='video',
                object_id=video_instance.id,
                locale=this_locale).save()

            end = datetime.now()
            set_channel_view_count(begin, end)

            meta = models.ChannelLocaleMeta.query.filter(
                    models.ChannelLocaleMeta.locale == this_locale,
                    models.ChannelLocaleMeta.channel == channel_id).first()

            self.assertEquals(meta.view_count, 2)
            begin = datetime.now()

            UserActivity(
                user=user4_id,
                action='view',
                date_actioned=datetime.now(),
                object_type='channel',
                object_id=channel_id,
                locale=this_locale).save()

            end = datetime.now()
            set_channel_view_count(begin, end)

            self.assertEquals(meta.view_count, 3)


from test.services.test_user_flows import BaseUserTestCase


class ESChannelTest(base.RockPackTestCase):

    def test_toggle(self):
        with self.app.test_client():
            self.app.test_request_context().push()
            if use_elasticsearch():

                def es_channel(id):
                    esc = ChannelSearch('en-us')
                    esc.add_id(channel.id)
                    return esc.channels()

                user = self.create_test_user()
                channel = models.Channel(
                    owner=user.id,
                    title='a title',
                    description='',
                    cover='',
                ).save()

                time.sleep(2)
                self.assertEquals(es_channel(channel.id)[0]['id'], channel.id)

                channel.deleted = True
                channel = channel.save()
                time.sleep(2)
                self.assertEquals(es_channel(channel.id), [])

                channel.deleted = False
                channel = channel.save()
                time.sleep(2)
                self.assertEquals(es_channel(channel.id)[0]['id'], channel.id)

                channel.public = False
                channel = channel.save()
                time.sleep(2)
                self.assertEquals(es_channel(channel.id), [])

                channel.deleted = True
                channel = channel.save()
                time.sleep(2)
                self.assertEquals(es_channel(channel.id), [])


class ChannelVisibleFlag(BaseUserTestCase):

    def test_visible_flag(self):
        with self.app.test_client():
            self.app.test_request_context().push()
            user = self.register_user()
            user_token = self.token

            if use_elasticsearch():
                new_title = 'a new channel title'
                new_description = 'this is a new description!'
                r = self.post(
                    self.urls['channels'],
                    dict(
                        title=new_title,
                        description=new_description,
                        category=3,
                        cover=RockpackCoverArtData.comic_cover.cover,
                        public=True
                    ),
                    token=self.token
                )
                owned_resource = r['resource_url']
                params = dict(q='music', size=1)
                videos = self.get(self.urls['video_search'], params=params)['videos']['items']

                self.put(owned_resource + 'videos/', [videos[0]['id']], token=self.token)
                time.sleep(2)

                resource = '{}/ws/{}/channels/{}/'.format(self.default_base_url, user['id'], r['id'])

                new_ch = models.Channel.query.filter_by(owner=user['id']).filter(
                    models.Channel.title == new_title).one()

                self.register_user()
                user2_token = self.token

                # Check user2 can see channel
                channel = self.get(resource, token=user2_token)
                self.assertEquals(channel['id'], r['id'])

                # Hide channel from user2
                ch = models.Channel.query.get(new_ch.id)
                ch.visible = False
                ch.save()
                self.assertEquals(models.Channel.query.get(new_ch.id).visible, False)

                time.sleep(2)
                # Owner should still be able to see channel
                r = self.get(owned_resource, token=user_token)
                self.assertEquals(channel['id'], r['id'])

                # Channel should be hidden from user2
                with self.assertRaises(Exception):  # Why doesn't this catch AssertionError???
                    self.get(resource, token=user2_token)


class ChannelCreateTestCase(base.RockPackTestCase):

    def test_new_channel(self):
        with self.app.test_client() as client:
            self.app.test_request_context().push()
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
            new_ch = models.Channel.query.filter_by(owner=user.id).filter(
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

            r = client.put(
                resource,
                data=json.dumps(dict(
                    title='A long title xxxxxxxxxxxxxxxxxxxxxxxx',
                    description='',
                    category='',
                    cover='',
                    public=False)
                ),
                content_type='application/json',
                headers=[get_auth_header(user.id)]
            )
            self.assertEquals(400, r.status_code, r.data)

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

    def test_dupe_channel_untitled(self):
        with self.app.test_client() as client:
            self.app.test_request_context().push()
            user = self.create_test_user()

            r = client.post(
                '/ws/{}/channels/'.format(user.id),
                data=json.dumps(dict(
                    title=app.config['UNTITLED_CHANNEL'] + ' 2',
                    description='',
                    category=1,
                    cover='',
                    public=False)
                ),
                content_type='application/json',
                headers=[get_auth_header(user.id)]
            )
            self.assertEquals(201, r.status_code)

            r = client.post(
                '/ws/{}/channels/'.format(user.id),
                data=json.dumps(dict(
                    title='',
                    description='',
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
            self.assertEquals(json.loads(r.data)['title'], app.config['UNTITLED_CHANNEL'] + ' 1')

            r = client.post(
                '/ws/{}/channels/'.format(user.id),
                data=json.dumps(dict(
                    title='',
                    description='',
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
            self.assertEquals(json.loads(r.data)['title'], app.config['UNTITLED_CHANNEL'] + ' 3')

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
                "title": ["Field cannot be longer than 25 characters."],
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

            self.wait_for_es()
            for user_id in user.id, user2_id:
                r = client.get('/ws/{}/'.format(user.id), headers=[get_auth_header(user_id)])
                self.assertEquals(200, r.status_code)
                channels = json.loads(r.data)['channels']
                titles = ['Favorites', 'updated', '2', '0']
                self.assertEquals([c['title'] for c in channels['items']], titles)

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

    def test_channel_cover(self):
        with self.app.test_client() as client:
            user_id = self.create_test_user().id
            r = client.post(
                '/ws/{}/channels/'.format(user_id),
                data=json.dumps(dict(title='', category='', description='', public='', cover='')),
                content_type='application/json',
                headers=[get_auth_header(user_id)]
            )
            self.assertEquals(201, r.status_code, r.data)
            resource = urlsplit(r.headers['Location']).path

            # Check for empty values
            data = json.loads(client.get(resource, headers=[get_auth_header(user_id)]).data)
            self.assertEquals('', data['cover']['thumbnail_url'])
            self.assertEquals(None, data['cover']['aoi'])

            for cover, code in [(RockpackCoverArtData.comic_cover.cover, 200),
                                ('KEEP', 200), ('keep', 400), ('', 200)]:
                r = client.put(
                    resource,
                    data=json.dumps(dict(title='', category='', description='', public='', cover=cover)),
                    content_type='application/json',
                    headers=[get_auth_header(user_id)]
                )
                self.assertEquals(code, r.status_code)

                data = json.loads(client.get(resource, headers=[get_auth_header(user_id)]).data)
                name = RockpackCoverArtData.comic_cover.cover.replace('.png', '.jpg') if cover else ''
                self.assertEquals(data['cover']['thumbnail_url'].split('/')[-1], name)

    def test_naughty_title(self):
        user_id = self.create_test_user().id
        with self.app.test_client() as client:
            for title, status in [
                    ('fuck rockpack', 400),
                    ('FuckRockpack', 400),
                    ('SHIT', 400),
                    ('shit!', 400),
                    ('OK!', 201),
                    ('scunthorpe', 201)]:
                r = client.post(
                    '/ws/{}/channels/'.format(user_id),
                    data=json.dumps(dict(title=title, category='', description='', public='', cover='')),
                    content_type='application/json',
                    headers=[get_auth_header(user_id)]
                )
                self.assertEquals(status, r.status_code, r.data)

    def test_public_private(self):
        user_id = self.create_test_user().id
        with self.app.test_client() as client:
            # create channel
            r = client.post(
                '/ws/{}/channels/'.format(user_id),
                data=json.dumps(dict(title='', category='', description='', public='', cover='')),
                content_type='application/json',
                headers=[get_auth_header(user_id)]
            )
            self.assertEquals(r.status_code, 201)
            resource = urlsplit(r.headers['Location']).path

            # add videos
            r = client.post(
                resource + 'videos/',
                data=json.dumps([VideoInstanceData.video_instance1.id]),
                content_type='application/json',
                headers=[get_auth_header(user_id)]
            )
            self.assertEquals(r.status_code, 204)

            for title, category, cover, public in (
                    ('test', '', '', False),
                    ('test', '1', '', False),
                    ('test', '1', RockpackCoverArtData.comic_cover.cover, False),
                    ('test', '1', RockpackCoverArtData.comic_cover.cover, True)):
                r = client.put(
                    resource,
                    data=json.dumps(dict(
                        title=title,
                        category=category,
                        cover=cover,
                        description='',
                        public=public,
                    )),
                    content_type='application/json',
                    headers=[get_auth_header(user_id)]
                )
                self.assertEquals(r.status_code, 200)

                r = client.get(resource, headers=[get_auth_header(user_id)])
                self.assertEquals(json.loads(r.data)['public'], public)
