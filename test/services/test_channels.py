import uuid
import json
from datetime import datetime, timedelta
from urlparse import urlsplit
from mock import patch
from test import base
from test.fixtures import RockpackCoverArtData, VideoInstanceData, VideoData, ChannelData
from test.test_decorators import skip_if_dolly, skip_if_rockpack, skip_unless_config
from test.test_helpers import get_auth_header
from test.services.test_user_flows import BaseUserTestCase
from rockpack.mainsite import app
from rockpack.mainsite.services.base.models import JobControl
from rockpack.mainsite.services.video.commands import update_channel_view_counts, update_channel_promotions
from rockpack.mainsite.core.es import use_elasticsearch
from rockpack.mainsite.core.es.search import VideoSearch
from rockpack.mainsite.services.video import models
from rockpack.mainsite.services.user.models import UserActivity


def search_video(videoid):
    v = VideoSearch('en-us')
    v.add_id(videoid)
    return v.videos()[0]


class ChannelViewCountPopulation(base.RockPackTestCase):

    @skip_unless_config('ELASTICSEARCH_URL')
    def test_star_counts(self):
        """ Populate the view count on channel locale meta """
        with self.app.test_request_context():
            with self.app.test_client() as client:
                user2_id = self.create_test_user().id
                user3_id = self.create_test_user().id
                user4_id = self.create_test_user().id

                videoid = VideoInstanceData.video_instance1.id

                client.post(
                    '/ws/{}/activity/?locale=en-us'.format(user2_id),
                    data=json.dumps(dict(action='star', video_instance=videoid)),
                    content_type='application/json',
                    headers=[get_auth_header(user2_id)])

            self.wait_for_es()

        with self.app.test_request_context():
            #self.wait_for_es()
            result = search_video(videoid)
            #self.assertEquals(1, result['video']['star_count'])

            with self.app.test_client() as client:
                client.post(
                    '/ws/{}/activity/?locale=en-us'.format(user3_id),
                    data=json.dumps(dict(action='star', video_instance=videoid)),
                    content_type='application/json',
                    headers=[get_auth_header(user3_id)])

        with self.app.test_request_context():
            self.wait_for_es()
            result = search_video(videoid)
            self.assertEquals(2, result['video']['star_count'])

            with self.app.test_client() as client:
                client.post(
                    '/ws/{}/activity/?locale=en-us'.format(user4_id),
                    data=json.dumps(dict(action='star', video_instance=videoid)),
                    content_type='application/json',
                    headers=[get_auth_header(user4_id)])

        with self.app.test_request_context():
            self.wait_for_es()
            result = search_video(videoid)
            self.assertEquals(3, result['video']['star_count'])

            with self.app.test_client() as client:

                vilm = models.VideoInstanceLocaleMeta.query.filter(
                    models.VideoInstanceLocaleMeta.video_instance == videoid).first()

                self.assertEquals(3, vilm.star_count)

    def test_populate(self):
        """ Populate the view count on channel locale meta """
        with self.app.test_client() as client:
            self.app.test_request_context().push()
            user = self.create_test_user()
            user2_id = self.create_test_user().id
            user3_id = self.create_test_user().id
            user4_id = self.create_test_user().id

            begin = datetime.utcnow()

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
                date_added=datetime.utcnow()
            ).save()

            video_instance = models.VideoInstance(
                channel=channel_id,
                video=VideoData.video1.id
            ).save()

            UserActivity(
                user=user2_id,
                action='view',
                date_actioned=datetime.utcnow(),
                object_type='channel',
                object_id=channel_id,
                locale=this_locale
            ).save()

            UserActivity(
                user=user3_id,
                action='view',
                date_actioned=datetime.utcnow(),
                object_type='video',
                object_id=video_instance.id,
                locale=this_locale
            ).save()

            JobControl(job='update_channel_view_counts', last_run=begin).save()
            update_channel_view_counts()

            meta = models.ChannelLocaleMeta.query.filter(
                models.ChannelLocaleMeta.locale == this_locale,
                models.ChannelLocaleMeta.channel == channel_id).first()

            self.assertEquals(meta.view_count, 2)

            UserActivity(
                user=user4_id,
                action='view',
                date_actioned=datetime.utcnow(),
                object_type='channel',
                object_id=channel_id,
                locale=this_locale).save()

            update_channel_view_counts()

            self.assertEquals(meta.view_count, 3)


class ChannelPromotionTest(base.RockPackTestCase):

    @skip_unless_config('ELASTICSEARCH_URL')
    def test_insert(self):
        user = self.create_test_user()

        with self.app.test_request_context():
            now = datetime.utcnow()
            models.ChannelPromotion(
                channel=ChannelData.channel1.id,
                date_start=now - timedelta(seconds=10),
                date_end=now + timedelta(seconds=30),
                category=0,
                locale='en-us',
                position=1
            ).save()

        update_channel_promotions()
        self.wait_for_es()

        with self.app.test_request_context():
            with self.app.test_client() as client:
                r = client.get(
                    '/ws/channels/',
                    content_type='application/json',
                    headers=[get_auth_header(user.id)]
                )

                feed = json.loads(r.data)
                self.assertEquals(feed['channels']['items'][0]['id'], ChannelData.channel1.id)


class ChannelDisplayTestCase(BaseUserTestCase):

    def test_visible_flag(self):
        with self.app.test_client() as client:
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
                if self.app.config.get('DOLLY'):
                    #XXX: Search isnt' going to work with ES off
                    # since we don't search over yt so attach
                    # a video manually
                    client.post(
                        owned_resource + 'videos/',
                        data=json.dumps([VideoInstanceData.video_instance1.id]),
                        content_type='application/json',
                        headers=[get_auth_header(user['id'])]
                    )
                else:
                    videos = self.get(self.urls['video_search'], params=params)['videos']['items']
                    self.put(owned_resource + 'videos/', [videos[0]['id']], token=self.token)

                self.wait_for_es()

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

                self.wait_for_es()

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
        created_order = ['Favorites', '2', 'updated', '0']
        if 'WATCH_LATER_CHANNEL' in app.config:
            created_order.insert(1, app.config['WATCH_LATER_CHANNEL'][0])
        self.assertEquals([c['title'] for c in r['channels']['items']], created_order)

        # Check public channels are order by date_updated
        r = self.get('{}/ws/{}/'.format(self.default_base_url, user['id']))
        self.assertEquals([c['title'] for c in r['channels']['items']],
                          ['Favorites', 'updated', '2', '0'])

    @skip_unless_config('WATCH_LATER_CHANNEL')
    def test_watch_later(self):
        with self.app.test_client():
            self.register_user()

            # watch later is present but not public
            r = self.get(self.urls['channels'], token=self.token)
            channel = next(c for c in r['channels']['items']
                           if c['title'] == app.config['WATCH_LATER_CHANNEL'][0])
            self.assertTrue(channel.get('watchlater'))
            self.assertFalse(channel['public'])

            # not editable
            with self.assertRaisesRegexp(self.failureException, '400'):
                self.request(channel['resource_url'], 'delete', token=self.token)

            # but can add videos
            self.post(channel['resource_url'] + 'videos/',
                      [VideoInstanceData.video_instance1.id], token=self.token)
            videos = dict(models.VideoInstance.query.
                          filter_by(channel=channel['id']).values('video', 'id'))
            self.assertIn(VideoInstanceData.video_instance1.video, videos)


class ChannelCreateTestCase(base.RockPackTestCase):

    @skip_if_dolly
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

            # test duplicate title (with change in case)
            r = client.post(
                '/ws/{}/channels/'.format(user.id),
                data=json.dumps(dict(
                    title=new_title.upper(),
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

    @skip_if_dolly
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
            normal_url = [c['resource_url'] for c in channels if not c.get('favourites') and not c.get('watchlater')][0]

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

    @skip_if_dolly
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

    @skip_if_dolly
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
                    VideoInstanceData.video_instance2.id,
                    VideoInstanceData.video_instance3.id,
                ]),
                content_type='application/json',
                headers=[get_auth_header(user_id)]
            )
            self.assertEquals(r.status_code, 204)
            positions = models.VideoInstance.query.filter_by(
                channel=channel_id).values('video', 'position')
            self.assertItemsEqual(positions, [
                (VideoData.video2.id, 0),
                (VideoData.video3.id, 1),
            ])

            self.wait_for_es()

        with self.app.test_client() as client:
            # Only run this part if es is turned on
            if app.config.get('DOLLY') and app.config.get('ELASTICSEARCH_URL'):
                self.assertEquals(VideoData.video2.category,
                                  models.Channel.query.get(channel_id).category)
            # change positions
            r = client.put(
                '/ws/{}/channels/{}/videos/'.format(user_id, channel_id),
                data=json.dumps([
                    VideoInstanceData.video_instance3.id,
                    VideoInstanceData.video_instance2.id,
                ]),
                content_type='application/json',
                headers=[get_auth_header(user_id)]
            )
            self.assertEquals(r.status_code, 204)
            positions = models.VideoInstance.query.filter_by(
                channel=channel_id).values('video', 'position')
            self.assertItemsEqual(positions, [
                (VideoData.video3.id, 0),
                (VideoData.video2.id, 1),
            ])

    @skip_if_rockpack
    @skip_unless_config('ELASTICSEARCH_URL')
    def test_video_comments(self):
        with app.test_request_context():
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

                # add comment
                instance_data = dict(userid=user_id, channelid=channel_id)

                r = client.get(
                    '/ws/{userid}/channels/{channelid}/'.format(**instance_data),
                    content_type='application/json',
                    headers=[get_auth_header(user_id)])

                instance_data['videoid'] = json.loads(r.data)['videos']['items'][0]['id']

                r = client.post(
                    '/ws/{userid}/channels/{channelid}/videos/{videoid}/comments/'.format(**instance_data),
                    data=json.dumps(dict(comment="this is a comment")),
                    content_type='application/json',
                    headers=[get_auth_header(user_id)]
                )
                self.assertEquals(r.status_code, 201)

                self.wait_for_es()

                v = VideoSearch('en-gb')
                v.add_id(instance_data['videoid'])
                instance = v.videos()[0]
                self.assertEquals(instance['comments']['total'], 1)

                # delete comment
                r = client.get(
                    '/ws/{userid}/channels/{channelid}/videos/{videoid}/comments/'.format(**instance_data),
                    content_type='application/json',
                    headers=[get_auth_header(user_id)]
                )

                comment_id = json.loads(r.data)['comments']['items'][0]['id']
                instance_data.update({'commentid': comment_id})

                r = client.delete(
                    '/ws/{userid}/channels/{channelid}/videos/{videoid}/comments/{commentid}/'.format(**instance_data),
                    content_type='application/json',
                    headers=[get_auth_header(user_id)]
                )

                self.wait_for_es()

                v = VideoSearch('en-gb')
                v.add_id(instance_data['videoid'])
                instance = v.videos()[0]
                self.assertEquals(instance['comments']['total'], 0)

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

    def test_original_channel_owner(self):
        user_id = self.create_test_user().id
        favourites = models.Channel.query.filter_by(
            owner=user_id, favourite=True).value('id')
        with self.app.test_request_context():
            with self.app.test_client() as client:
                r = client.post(
                    '/ws/{}/channels/{}/videos/'.format(user_id, favourites),
                    data=json.dumps([
                        ('youtube', VideoData.video1.source_videoid),
                        VideoInstanceData.video_instance2.id,
                        VideoInstanceData.video_instance3.id,
                    ]),
                    content_type='application/json',
                    headers=[get_auth_header(user_id)]
                )
                self.assertEquals(r.status_code, 204)

        self.wait_for_es()

        with self.app.test_request_context():
            with self.app.test_client() as client:
                r = client.get('/ws/{}/channels/{}/videos/'.format(user_id, favourites))
                orig_map = [(v['video']['id'], v.get('original_channel_owner', {}).get('id'))
                            for v in json.loads(r.data)['videos']['items']]
                self.assertItemsEqual(orig_map, [
                    (VideoData.video1.id, None),
                    (VideoInstanceData.video_instance2.video, ChannelData.channel2.owner),
                    (VideoInstanceData.video_instance3.video, VideoInstanceData.video_instance3.original_channel_owner),
                ])
