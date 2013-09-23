import uuid
import time
import json
from datetime import datetime, timedelta
from urlparse import urlsplit
from mock import patch
from test import base
from test.fixtures import RockpackCoverArtData, VideoInstanceData, VideoData, ChannelData
from test.test_helpers import get_auth_header
from test.services.test_user_flows import BaseUserTestCase
from rockpack.mainsite import app
from rockpack.mainsite.services.video.commands import set_channel_view_count, update_channel_promo_activity
from rockpack.mainsite.core.es import use_elasticsearch
from rockpack.mainsite.core.es.search import ChannelSearch
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
                date_added=datetime.now()
            ).save()

            video_instance = models.VideoInstance(
                channel=channel_id,
                video=VideoData.video1.id
            ).save()

            UserActivity(
                user=user2_id,
                action='view',
                date_actioned=datetime.now(),
                object_type='channel',
                object_id=channel_id,
                locale=this_locale
            ).save()

            UserActivity(
                user=user3_id,
                action='view',
                date_actioned=datetime.now(),
                object_type='video',
                object_id=video_instance.id,
                locale=this_locale
            ).save()

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


class ChannelPromotionTest(base.RockPackTestCase):

    def test_insert(self):
        with self.app.test_client() as client:
            self.app.test_request_context().push()

            if use_elasticsearch():
                now = datetime.utcnow()
                models.ChannelPromotion(
                    channel=ChannelData.channel1.id,
                    date_start=now - timedelta(seconds=10),
                    date_end=now + timedelta(seconds=30),
                    category=0,
                    locale='en-us',
                    position=1
                ).save()

                update_channel_promo_activity()
                user = self.create_test_user()

                time.sleep(2)

                r = client.get(
                    '/ws/channels/',
                    content_type='application/json',
                    headers=[get_auth_header(user.id)]
                )

                feed = json.loads(r.data)
                self.assertEquals(feed['channels']['items'][0]['id'], ChannelData.channel1.id)


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

    @patch('sqlalchemy.dialects.sqlite.base.SQLiteCompiler.visit_now_func')
    def test_channel_order(self, now_func):
        # Need to clear the compiled statement cache on the table mapper
        # so that the value for "now" is changed.
        def set_now(month, day):
            compiled_cache.clear()
            now_func.return_value = 'datetime("2013-%02d-%02dT00:00:00")' % (month, day)
        from sqlalchemy import inspect
        compiled_cache = inspect(models.Channel)._compiled_cache

        set_now(1, 1)
        user = self.register_user()

        c1 = None
        for i in range(3):
            set_now(2, i + 1)
            r = self.post(
                self.urls['channels'],
                data=dict(
                    title=str(i),
                    description='',
                    category='1',
                    cover=RockpackCoverArtData.comic_cover.cover,
                    public=True,
                ),
                token=self.token,
            )
            if i == 1:
                c1 = r['resource_url']
            r = self.post(
                r['resource_url'] + 'videos/',
                data=[VideoInstanceData.video_instance1.id],
                token=self.token,
            )

        set_now(3, 1)
        r = self.put(
            c1,
            data=dict(
                title='updated',
                description='x',
                category='1',
                cover=RockpackCoverArtData.comic_cover.cover,
                public=True,
            ),
            token=self.token,
        )

        self.wait_for_es()

        # Check own channels are ordered by date_created
        r = self.get(self.urls['user'], token=self.token)
        self.assertEquals([c['title'] for c in r['channels']['items']],
                          ['Favorites', '2', 'updated', '0'])

        # Check public channels are order by date_updated
        r = self.get('{}/ws/{}/'.format(self.default_base_url, user['id']))
        self.assertEquals([c['title'] for c in r['channels']['items']],
                          ['Favorites', 'updated', '2', '0'])


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
            self.assertFalse(resp['public'], 'channel should be private')
            self.assertIsNone(resp['date_published'])

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
            channel = models.Channel.query.get(new_ch.id)
            self.assertTrue(channel.public, 'channel should be public')
            self.assertIsNotNone(channel.date_published)
            self.assertGreaterEqual(channel.date_published, channel.date_added)

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


class ChannelVideoTestCase(base.RockPackTestCase):

    def test_channel_videos(self):
        user_id = self.create_test_user().id
        with self.app.test_client() as client:
            # create new channel
            r = client.post(
                '/ws/{}/channels/'.format(user_id),
                data=json.dumps(dict(
                    title='test',
                    description='test',
                    category='',
                    cover='',
                    public=True,
                )),
                content_type='application/json',
                headers=[get_auth_header(user_id)]
            )
            self.assertEquals(r.status_code, 201)
            channel_id = json.loads(r.data)['id']

            # add videos
            r = client.put(
                '/ws/{}/channels/{}/videos/'.format(user_id, channel_id),
                data=json.dumps([
                    VideoInstanceData.video_instance1.id,
                    VideoInstanceData.video_instance2.id,
                ]),
                content_type='application/json',
                headers=[get_auth_header(user_id)]
            )
            self.assertEquals(r.status_code, 204)
            positions = models.VideoInstance.query.filter_by(
                channel=channel_id).values('video', 'position')
            self.assertItemsEqual(positions, [
                (VideoData.video1.id, 0),
                (VideoData.video2.id, 1),
            ])

            # change positions
            r = client.put(
                '/ws/{}/channels/{}/videos/'.format(user_id, channel_id),
                data=json.dumps([
                    VideoInstanceData.video_instance2.id,
                    VideoInstanceData.video_instance1.id,
                ]),
                content_type='application/json',
                headers=[get_auth_header(user_id)]
            )
            self.assertEquals(r.status_code, 204)
            positions = models.VideoInstance.query.filter_by(
                channel=channel_id).values('video', 'position')
            self.assertItemsEqual(positions, [
                (VideoData.video2.id, 0),
                (VideoData.video1.id, 1),
            ])


    def test_channel_source(self):
        user_id = self.create_test_user().id
        favourites = models.Channel.query.filter_by(
            owner=user_id, favourite=True).value('id')
        with self.app.test_client() as client:
            r = client.post(
                '/ws/{}/channels/{}/videos/'.format(user_id, favourites),
                data=json.dumps([
                    ('youtube', VideoData.video1.source_videoid),
                    VideoInstanceData.video_instance2.id,
                ]),
                content_type='application/json',
                headers=[get_auth_header(user_id)]
            )
            self.assertEquals(r.status_code, 204)
            # Check that video from youtube doesn't have source_channel
            # and video from video_instance2 references the source channel
            src_map = models.VideoInstance.query.filter_by(
                channel=favourites).values('video', 'source_channel')
            self.assertItemsEqual(src_map, [
                (VideoData.video1.id, None),
                (VideoData.video2.id, VideoInstanceData.video_instance2.channel)
            ])
