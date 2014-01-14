import json
import uuid
import cgi
import urlparse
from datetime import datetime, timedelta
from mock import patch
from test import base
from test.assets import AVATAR_IMG_PATH
from test.fixtures import UserData, ChannelData, VideoData, VideoInstanceData, CategoryData
from test.test_decorators import skip_unless_config
from test.test_helpers import get_auth_header
from test.test_helpers import get_client_auth_header
from rockpack.mainsite import app
from rockpack.mainsite.services.video.models import Channel
from rockpack.mainsite.services.oauth.api import ExternalUser
from rockpack.mainsite.services.oauth.models import ExternalToken, ExternalFriend
from rockpack.mainsite.services.user.models import (
    User, UserActivity, UserAccountEvent, UserFlag, UserNotification,
    UserContentFeed, UserSubscriptionRecommendation, Subscription)
from rockpack.mainsite.services.user import commands as cron_cmds
from rockpack.mainsite.services.user.api import add_videos_to_channel


class TestAPNS(base.RockPackTestCase):

    def test_add_device_token(self):
        with self.app.test_client() as client:
            self.app.test_request_context().push()
            user = self.create_test_user()
            token = uuid.uuid4().hex
            system = 'apns'
            client.post(
                '/ws/{}/external_accounts/'.format(user.id),
                data=json.dumps(dict(external_system=system, external_token=token)),
                content_type='application/json',
                headers=[get_auth_header(user.id)],
            )
            self.assertEquals(
                ExternalToken.query.filter_by(
                    external_system=system,
                    external_token=token).count(),
                1
            )

            new_token = uuid.uuid4().hex

            client.post(
                '/ws/{}/external_accounts/'.format(user.id),
                data=json.dumps(dict(external_system=system, external_token=new_token)),
                content_type='application/json',
                headers=[get_auth_header(user.id)],
            )

            etoken = ExternalToken.query.filter_by(
                external_system=system,
                external_token=new_token).one()
            self.assertEquals(new_token, etoken.external_token)
            self.assertEquals(user.id, etoken.external_uid)

    def test_send_notification(self):
        def _notification_data(user):
            return {
                "user": {
                    "avatar_thumbnail_url": "http://media.us.rockpack.com/images/avatar/thumbnail_medium/2UQj6d1FKhUP_5Im60zErg.jpg",
                    "resource_url": "http://api.rockpack.com/ws/%s/" % user.id,
                    "display_name": user.display_name,
                    "id": user.id
                },
                "channel": {
                    "resource_url": "https://secure.rockpack.com/ws/sEL2DlUxRPaeLTwaOS3e2A/channels/chz_vBOu-fTgWiT15kuGV4Pw/",
                    "thumbnail_url": "http://media.us.rockpack.com/images/channel/thumbnail_medium/fav2.jpg",
                    "id": "chz_vBOu-fTgWiT15kuGV4Pw"
                }
            }

        with self.app.test_client() as client:
            self.app.test_request_context().push()
            user = self.create_test_user()
            client.post(
                '/ws/{}/external_accounts/'.format(user.id),
                data=json.dumps(dict(external_system='apns', external_token=uuid.uuid4().hex)),
                content_type='application/json',
                headers=[get_auth_header(user.id)],
            )

            ndata = _notification_data(user)

            un = UserNotification(
                user=user.id,
                message_type='subscribed',
                message=json.dumps(ndata)
            ).save()

            def _new_send(obj, message):
                # simulate success
                return apnsclient.Result(message)

            app.config['ENABLE_APNS_DEEPLINKS'] = True

            import apnsclient
            from rockpack.mainsite.services.user.commands import send_push_notifications
            with patch.object(apnsclient.APNs, 'send', _new_send):
                result = send_push_notifications(user)
                self.assertFalse(result.failed or result.errors)
                message = result.message.payload
                self.assertEquals(user.display_name, message['aps']['alert']['loc-args'][0])
                self.assertEquals(1, message['aps']['badge'])
                self.assertEquals(un.id, message['id'])
                self.assertEquals(
                    urlparse.urlparse(ndata['channel']['resource_url']).path.lstrip('/ws/'),
                    message['url']
                )

    def test_invalidate_tokens(self):
        with self.app.test_client() as client:
            self.app.test_request_context().push()
            user = self.create_test_user()
            device_token = uuid.uuid4().hex
            client.post(
                '/ws/{}/external_accounts/'.format(user.id),
                data=json.dumps(dict(external_system='apns', external_token=device_token)),
                content_type='application/json',
                headers=[get_auth_header(user.id)],
            )

            def _new_feedback(obj):
                return [(device_token, datetime.now() - timedelta(days=1))]

            import apnsclient
            from rockpack.mainsite.services.user.commands import _invalidate_apns_tokens
            with patch.object(apnsclient.APNs, 'feedback', _new_feedback):
                _invalidate_apns_tokens()
                self.assertEquals(0, ExternalToken.query.filter_by(external_token=device_token).count())


class TestProfileEdit(base.RockPackTestCase):

    @patch('rockpack.mainsite.services.oauth.api.ExternalUser.get_new_token')
    @patch('rockpack.mainsite.services.oauth.api.ExternalUser._get_external_data')
    def test_external_accounts(self, get_external_data, get_new_token):
        get_external_data.return_value = dict(id='1')
        get_new_token.return_value = ExternalUser('facebook', 'xxx', 86400)
        with self.app.test_client() as client:
            def check_connect(userid, status):
                r = client.post(
                    '/ws/{}/external_accounts/'.format(userid),
                    data=json.dumps(dict(
                        external_system='facebook',
                        external_token='xxx',
                        token_expires='2020-01-01T00:00:00',
                    )),
                    content_type='application/json',
                    headers=[get_auth_header(userid)],
                )
                self.assertEquals(r.status_code, status, r.data)
                return r

            user1 = self.create_test_user().id
            user2 = self.create_test_user().id

            # check initial connect
            check_connect(user1, 201)

            # confirm that you can't connect the same account to another user
            check_connect(user2, 400)

            # confirm that you can't connect a different account to an existing user
            get_external_data.return_value = dict(id='2')
            check_connect(user1, 400)

            # can connect new account to other user
            check_connect(user2, 201)
            r = client.get('/ws/{}/external_accounts/'.format(user2),
                           headers=[get_auth_header(user2)])
            ids = [i['external_uid'] for i in json.loads(r.data)['external_accounts']['items']
                   if i['external_system'] == 'facebook']
            self.assertEquals(ids, ['2'])

    def test_change_username(self):
        with self.app.test_client() as client:
            existing_user = self.create_test_user()

            new_user = self.create_test_user()
            r = client.put(
                '/ws/{}/username/'.format(new_user.id),
                data=json.dumps(existing_user.username),
                content_type='application/json',
                headers=[get_auth_header(new_user.id)],
            )
            data = json.loads(r.data)
            self.assertEquals(r.status_code, 400)
            self.assertEquals(['"{}" already taken.'.format(existing_user.username)], data['message'])
            assert 'suggested_username' in data

            r = client.put(
                '/ws/{}/username/'.format(new_user.id),
                data=json.dumps('lemonademan'),
                content_type='application/json',
                headers=[get_auth_header(new_user.id)],
            )
            self.assertEquals(r.status_code, 204)

    def test_fullname_toggle(self):
        with self.app.test_client() as client:
            new_user = self.create_test_user()

            r = client.get(
                '/ws/{}/'.format(new_user.id),
                content_type='application/json',
                headers=[get_auth_header(new_user.id)])
            old_data = json.loads(r.data)

            client.put(
                '/ws/{}/display_fullname/'.format(new_user.id),
                data=json.dumps(False),
                content_type='application/json',
                headers=[get_auth_header(new_user.id)],
            )
            r = client.get(
                '/ws/{}/'.format(new_user.id),
                content_type='application/json',
                headers=[get_auth_header(new_user.id)])
            new_data = json.loads(r.data)

            self.assertNotEquals(old_data['display_name'], new_data['display_name'])
            self.assertEquals(new_data['username'], new_data['display_name'])

    def test_password_change(self):
        with self.app.test_client() as client:
            new_user = self.create_test_user()
            r = client.put(
                '/ws/{}/{}/'.format(new_user.id, 'password'),
                data=json.dumps(dict(old='password', new='imbatman')),
                content_type='application/json',
                headers=[get_auth_header(new_user.id)],
            )
            creds = json.loads(r.data)

            r = client.post(
                '/ws/token/',
                headers=[get_client_auth_header()],
                data=dict(refresh_token=creds['refresh_token'],
                grant_type='refresh_token'))

            new_creds = json.loads(r.data)

            self.assertEquals('Bearer', new_creds['token_type'], 'token type should be Bearer')
            self.assertEquals(new_creds['refresh_token'], creds['refresh_token'], 'refresh tokens should be the same')
            self.assertNotEquals(
                new_creds['access_token'],
                creds['access_token'],
                'old access token should not be the same at the new one')

    def test_failed_password_length(self):
        with self.app.test_client() as client:
            new_user = self.create_test_user()
            r = client.put(
                '/ws/{}/{}/'.format(new_user.id, 'password'),
                data=json.dumps(dict(old='password', new='4char')),
                content_type='application/json',
                headers=[get_auth_header(new_user.id)],
            )
            data = json.loads(r.data)
            self.assertEquals(data['message'], ["Field must be at least 6 characters long."])

    def test_failed_old_password(self):
        with self.app.test_client() as client:
            new_user = self.create_test_user()
            r = client.put(
                '/ws/{}/{}/'.format(new_user.id, 'password'),
                data=json.dumps(dict(old='wrong', new='6chars')),
                content_type='application/json',
                headers=[get_auth_header(new_user.id)],
            )
            data = json.loads(r.data)
            self.assertEquals(data['message'], ["Old password is incorrect."])

    def test_empty_password(self):
        with self.app.test_client() as client:
            user1 = self.create_test_user(password='testing')
            user2 = self.create_test_user(password=None)
            for userid, status in ((user1.id, 400), (user2.id, 200)):
                r = client.put(
                    '/ws/{}/{}/'.format(userid, 'password'),
                    data=json.dumps(dict(old='', new='rockpack')),
                    content_type='application/json',
                    headers=[get_auth_header(userid)],
                )
                self.assertEquals(r.status_code, status)

    def test_failed_password(self):
        with self.app.test_client() as client:
            new_user = self.create_test_user()
            r = client.put(
                '/ws/{}/{}/'.format(new_user.id, 'password'),
                data=json.dumps({}),
                content_type='application/json',
                headers=[get_auth_header(new_user.id)],
            )
            data = json.loads(r.data)
            self.assertEquals(data['message'], ["Both old and new passwords must be supplied."])

    def test_other_fields(self):
        with self.app.test_client() as client:
            new_user = self.create_test_user()
            field_map = {
                "first_name": 'James',
                "last_name": 'Hong',
                "email": 'bigtrouble@littlechina.com',
                "locale": 'en-us',
                "gender": "m",
                "date_of_birth": '1901-01-01'}

            for field, value in field_map.iteritems():
                r = client.put(
                    '/ws/{}/{}/'.format(new_user.id, field),
                    data=json.dumps(value),
                    content_type='application/json',
                    headers=[get_auth_header(new_user.id)],
                )
                self.assertEquals(r.status_code, 204, "{} - {}".format(field, r.data))

            user = User.query.get(new_user.id)
            self.assertEquals(field_map['locale'], user.locale)
            self.assertEquals(field_map['email'], user.email)
            self.assertEquals(field_map['gender'], user.gender)
            self.assertEquals(field_map['last_name'], user.last_name)
            self.assertEquals(field_map['first_name'], user.first_name)
            self.assertEquals(field_map['date_of_birth'], user.date_of_birth.strftime("%Y-%m-%d"))

    def test_profile_cover(self):
        with self.app.test_client() as client:
            new_user = self.create_test_user()
            r = client.put(
                '/ws/{}/{}/'.format(new_user.id, 'profile_cover'),
                data={'image': (AVATAR_IMG_PATH, 'cover.jpg')},
                headers=[get_auth_header(new_user.id)],
            )
            self.assertEquals(r.status_code, 200)
            self.assertIn('thumbnail_url', json.loads(r.data))

    def test_brand_profile_cover(self):
        with self.app.test_client() as client:
            self.app.test_request_context().push()
            new_user = self.create_test_user(brand_profile_cover='tmp.jpg')
            r = client.put(
                '/ws/{}/{}/'.format(new_user.id, 'profile_cover'),
                data={'image': (AVATAR_IMG_PATH, 'cover.jpg')},
                headers=[get_auth_header(new_user.id)],
            )
            self.assertEquals(r.status_code, 200)
            self.assertIn('thumbnail_url', json.loads(r.data))
            self.assertTrue(new_user.brand)
            self.assertFalse(bool(new_user.profile_cover))

            self.wait_for_es()
            r = client.get(
                '/ws/{}/'.format(new_user.id),
                headers=[get_auth_header(self.create_test_user().id)],
            )
            data = json.loads(r.data)
            self.assertTrue(data.get('brand'))
            self.assertIn('brand', data['profile_cover_url'])


class TestUserContent(base.RockPackTestCase):

    @skip_unless_config('ELASTICSEARCH_URL')
    def test_content_feed(self):
        with self.app.test_client() as client:
            self.app.test_request_context().push()
            user1 = self.create_test_user().id
            user2 = self.create_test_user().id
            user3 = self.create_test_user().id

            # Create new channel with a few videos and subscribe user
            channel1 = Channel.query.filter_by(owner=user1).one()
            c1instances = channel1.add_videos(
                v.id for v in VideoData.__dict__.values() if hasattr(v, 'id'))
            Subscription(user=user1, channel=channel1.id).save()

            # Add some stars to the second video
            c1starred = c1instances[1]
            for user in user1, user2, user3:
                UserActivity(user=user, action='star', object_type='video_instance',
                             object_id=c1starred.id).save()
            c1starred.star_count = 3
            c1starred.save()

            # Create a new channel owned by the owner of a subscription
            u2old = Channel.query.filter_by(owner=user2).limit(1).value('id')
            u2new = Channel(owner=user2, title='u2new', description='', cover='',
                            public=True, date_published=datetime.now()).save().id
            Subscription(user=user1, channel=u2old).save()

            # Create a new channel owner by a friend
            ExternalFriend(user=user1, external_system='facebook', external_uid='u3',
                           name='u3', avatar_url='').save()
            ExternalToken(user=user3, external_system='facebook', external_uid='u3',
                          external_token='u3u3').save()
            u3new = Channel(owner=user3, title='u3new', description='', cover='',
                            public=True, date_published=datetime.now()).save().id

            # Run cron commands
            date_from, date_to = datetime(2012, 1, 1), datetime(2020, 1, 1)
            cron_cmds.create_new_video_feed_items(date_from, date_to)
            cron_cmds.create_new_channel_feed_items(date_from, date_to)
            #cron_cmds.update_video_feed_item_stars(date_from, date_to)
            User.query.session.commit()

            # Fetch feed
            self.wait_for_es()
            r = client.get('/ws/{}/content_feed/'.format(user1),
                           headers=[get_auth_header(user1)])
            self.assertEquals(r.status_code, 200)
            data = json.loads(r.data)['content']
            self.assertEquals(data['total'], len(c1instances) + 2)
            itemids = [i['id'] for i in data['items']]

            # Check videos from channel1 (except c1starred) are present and aggregated
            self.assertIn(c1instances[0].id, itemids)
            agg = [a for a in data['aggregations'].values() if a['type'] == 'video'][0]
            self.assertEquals(agg['count'], len(c1instances) - 1)

            # Check stars on c1starred and that no stars on cover video
            self.assertNotIn(c1starred.id, agg['covers'])
            cover = [i for i in data['items'] if i['id'] == agg['covers'][0]][0]
            self.assertEquals(cover['video']['star_count'], 0)
            starred = [i for i in data['items'] if i['id'] == c1starred.id][0]
            self.assertEquals(starred['video']['star_count'], 3)
            self.assertItemsEqual([u['id'] for u in starred['starring_users']], [user1, user2, user3])

            # Check that new channels from friend and from subscription owner are present
            self.assertNotIn(u2old, itemids)
            self.assertIn(u2new, itemids)
            self.assertIn(u3new, itemids)

    @skip_unless_config('ELASTICSEARCH_URL')
    def test_channel_recommendations(self):
        self.app.config['RECOMMENDER_CATEGORY_BOOSTS'] = dict(
            gender={'f': ((2, 1.40),)},
        )
        with self.app.test_client() as client:
            self.app.test_request_context().push()
            user = self.create_test_user(gender='f')
            self.wait_for_es()
            r = client.get(
                '/ws/{}/channel_recommendations/'.format(user.id),
                headers=[get_auth_header(user.id)])
            self.assertEquals(r.status_code, 200)
            channels = json.loads(r.data)['channels']['items']
            first = channels[0]
            self.assertEquals(first['category'], 2)
            self.assertIn('cat-2-1.40', first['tracking_code'])

    def test_user_recommendations(self):
        UserSubscriptionRecommendation(
            user=UserData.test_user_a.id,
            category=CategoryData.Music.id,
        ).save()
        with self.app.test_client() as client:
            user = self.create_test_user()
            r = client.get(
                '/ws/{}/user_recommendations/'.format(user.id),
                headers=[get_auth_header(user.id)])
            self.assertEquals(r.status_code, 200)
            users = json.loads(r.data)['users']['items']
            self.assertListEqual([UserData.test_user_a.id], [u['id'] for u in users])
            # Recommended users should have description & category fields:
            self.assertIn('description', users[0])
            self.assertIn('category', users[0])

    def test_subscribe_all(self):
        with self.app.test_client() as client:
            self.app.test_request_context().push()
            user = self.create_test_user().id
            owner = self.create_test_user().id
            r = client.post(
                '/ws/{}/activity/'.format(user),
                data=json.dumps(dict(
                    action='subscribe_all',
                    object_type='user',
                    object_id=owner,
                )),
                content_type='application/json',
                headers=[get_auth_header(user)])
            self.assertEquals(r.status_code, 204)

            r = client.get(
                '/ws/{}/activity/'.format(user),
                headers=[get_auth_header(user)])
            activity = json.loads(r.data)
            self.assertIn(owner, activity['user_subscribed'])
            self.assertGreater(len(activity['subscribed']), 0)

            r = client.get('/ws/{}/'.format(owner),
                           headers=[get_auth_header(owner)])
            user_data = json.loads(r.data)
            self.assertGreater(user_data['subscriber_count'], 0)

    def test_unsubscribe_all(self):
        with self.app.test_client() as client:
            self.app.test_request_context().push()
            user = self.create_test_user().id
            owner = self.create_test_user().id
            channels = [i for i, in Channel.query.filter_by(owner=owner).values('id')]

            r = client.post(
                '/ws/{}/activity/'.format(user),
                data=json.dumps(dict(
                    action='subscribe_all',
                    object_type='user',
                    object_id=owner,
                )),
                content_type='application/json',
                headers=[get_auth_header(user)])
            self.assertEquals(r.status_code, 204)

            r = client.get(
                '/ws/{}/'.format(user),
                query_string=dict(data=['activity', 'subscriptions']),
                headers=[get_auth_header(user)])
            user_data = json.loads(r.data)
            self.assertListEqual([owner], user_data['activity']['user_subscribed'])
            self.assertListEqual(channels, user_data['activity']['subscribed'])
            self.assertListEqual(channels, [c['id'] for c in user_data['subscriptions']['items']])

            r = client.post(
                '/ws/{}/activity/'.format(user),
                data=json.dumps(dict(
                    action='unsubscribe_all',
                    object_type='user',
                    object_id=owner,
                )),
                content_type='application/json',
                headers=[get_auth_header(user)])
            self.assertEquals(r.status_code, 204)

            r = client.get(
                '/ws/{}/'.format(user),
                query_string=dict(data=['activity', 'subscriptions']),
                headers=[get_auth_header(user)])
            user_data = json.loads(r.data)
            self.assertListEqual([], user_data['activity']['user_subscribed'])
            self.assertListEqual([], user_data['activity']['subscribed'])
            self.assertListEqual([], [c['id'] for c in user_data['subscriptions']['items']])

    def test_activity_duplicates(self):
        with self.app.test_client() as client:
            user = self.create_test_user().id
            instance_id = VideoInstanceData.video_instance1.id
            for action in 'star', 'unstar', 'star', 'unstar':
                r = client.post(
                    '/ws/{}/activity/'.format(user),
                    data=json.dumps(dict(
                        action=action,
                        object_type='video_instance',
                        object_id=instance_id,
                    )),
                    content_type='application/json',
                    headers=[get_auth_header(user)])
                self.assertEquals(r.status_code, 204)

                r = client.get(
                    '/ws/{}/activity/'.format(user),
                    headers=[get_auth_header(user)])
                self.assertItemsEqual(
                    json.loads(r.data)['recently_starred'],
                    [instance_id] if action == 'star' else [])

    def test_activity_notifications(self):
        with self.app.test_client() as client:
            self.app.test_request_context().push()
            user = self.create_test_user().id
            owner = self.create_test_user().id
            channel = Channel.query.filter_by(owner=owner).first()
            video = channel.add_videos([VideoData.video1.id])[0]

            UserActivity(user=user, action='subscribe',
                         object_type='channel', object_id=channel.id).save()
            UserActivity(user=user, action='star',
                         object_type='video_instance', object_id=video.id).save()
            cron_cmds.create_new_activity_notifications()
            UserNotification.query.session.commit()

            r = client.get(
                '/ws/{}/notifications/'.format(owner),
                headers=[get_auth_header(owner)])
            self.assertEquals(r.status_code, 200)

            notifications = json.loads(r.data)['notifications']['items']
            self.assertEquals(len(notifications), 2)
            for notification in notifications:
                self.assertFalse(notification['read'])
                self.assertIn(notification['message_type'], ('subscribed', 'starred'))
                message = notification['message']
                self.assertEquals(message['user']['id'], user)
                if notification['message_type'] == 'subscribed':
                    self.assertEquals(message['channel']['id'], channel.id)
                    self.assertEquals(message['channel']['resource_url'], channel.resource_url)
                else:
                    self.assertEquals(message['video']['id'], video.id)
                    self.assertEquals(message['video']['channel']['id'], channel.id)

    def test_repack_notifications(self):
        with self.app.test_client() as client:
            self.app.test_request_context().push()
            user1 = self.create_test_user()
            user2 = self.create_test_user()
            channel1 = user1.channels[0]
            channel2 = Channel.create(owner=user2.id, title='new', description='',
                                      cover='comic', category=1)
            video1 = channel1.add_videos([VideoData.video1.id])[0]

            Channel.query.session.commit()
            add_videos_to_channel(channel2, [video1.id], None)
            cron_cmds.create_new_repack_notifications()
            UserNotification.query.session.commit()

            r = client.get(
                '/ws/{}/notifications/'.format(user1.id),
                headers=[get_auth_header(user1.id)])
            self.assertEquals(r.status_code, 200)

            notification, = json.loads(r.data)['notifications']['items']
            self.assertEquals(notification['message_type'], 'repack')
            self.assertEquals(notification['message']['user']['id'], user2.id)
            self.assertEquals(notification['message']['video']['channel']['id'], channel2.id)

    def test_unavailable_notifications(self):
        with self.app.test_client() as client:
            self.app.test_request_context().push()
            user = self.create_test_user()
            video = user.channels[0].add_videos([VideoData.video1.id])[0]
            UserNotification.query.session.commit()
            video.video_rel.visible = False
            UserNotification.query.session.commit()
            cron_cmds.create_unavailable_notifications()
            UserNotification.query.session.commit()

            r = client.get(
                '/ws/{}/notifications/'.format(user.id),
                headers=[get_auth_header(user.id)])
            self.assertEquals(r.status_code, 200)
            print json.dumps(json.loads(r.data), indent=True)

            notification, = json.loads(r.data)['notifications']['items']
            self.assertEquals(notification['message_type'], 'unavailable')
            self.assertEquals(notification['message']['user']['id'], user.id)
            self.assertEquals(notification['message']['video']['id'], video.id)

    def test_registration_notifications(self):
        with self.app.test_client() as client:
            self.app.test_request_context().push()
            user1 = self.create_test_user().id
            user2 = self.create_test_user().id
            ExternalFriend(user=user1, external_system='facebook', external_uid='u2',
                           name='u2', avatar_url='').save()
            ExternalToken(user=user2, external_system='facebook', external_uid='u2',
                          external_token='xxx').save()

            cron_cmds.create_new_registration_notifications()
            UserNotification.query.session.commit()

            r = client.get(
                '/ws/{}/notifications/'.format(user1),
                headers=[get_auth_header(user1)])
            self.assertEquals(r.status_code, 200)

            notification, = json.loads(r.data)['notifications']['items']
            self.assertEquals(notification['message_type'], 'joined')
            self.assertEquals(notification['message']['user']['id'], user2)

    def test_subscription_notification(self):
        with self.app.test_client() as client:
            self.app.test_request_context().push()
            user = self.create_test_user()
            channel = Channel.query.get(ChannelData.channel1.id)
            r = client.post(
                '/ws/{}/subscriptions/'.format(user.id),
                data=json.dumps(channel.resource_url),
                content_type='application/json',
                headers=[get_auth_header(user.id)])
            self.assertEquals(r.status_code, 201)

            self.assertIn(
                ('subscribe', channel.id),
                UserActivity.query.filter_by(user=user.id).values('action', 'object_id'))

            cron_cmds.create_new_activity_notifications()
            UserNotification.query.session.commit()
            notification = UserNotification.query.filter_by(
                user=channel.owner, message_type='subscribed').one()
            message = json.loads(notification.message)
            self.assertEquals(message['user']['id'], user.id)
            self.assertEquals(message['channel']['id'], channel.id)

    def test_star_notification(self):
        with self.app.test_client() as client:
            self.app.test_request_context().push()
            user = self.create_test_user()
            owner = self.create_test_user()
            video_instance = owner.channels[0].add_videos([VideoData.video1.id])[0]
            User.query.session.commit()

            r = client.post(
                '/ws/{}/activity/'.format(user.id),
                data=json.dumps(dict(action='star', video_instance=video_instance.id)),
                content_type='application/json',
                headers=[get_auth_header(user.id)])
            self.assertEquals(r.status_code, 204)

            self.assertIn(
                ('star', video_instance.id),
                UserActivity.query.filter_by(user=user.id).values('action', 'object_id'))

            cron_cmds.create_new_activity_notifications()
            UserNotification.query.session.commit()
            notification = UserNotification.query.filter_by(
                user=owner.id, message_type='starred').one()
            message = json.loads(notification.message)
            self.assertEquals(message['user']['id'], user.id)
            self.assertEquals(message['video']['id'], video_instance.id)

    def test_activity_tracking(self):
        with self.app.test_client() as client:
            self.app.test_request_context().push()
            r = client.get('/ws/channels/?category=4')
            self.assertEquals(r.status_code, 200)
            channel = json.loads(r.data)['channels']['items'][0]

            user = self.create_test_user()
            r = client.post(
                '/ws/{}/activity/?tracking_code={}'.format(user.id, channel['tracking_code']),
                data=json.dumps(dict(
                    action='open',
                    object_type='channel',
                    object_id=channel['id'])),
                content_type='application/json',
                headers=[get_auth_header(user.id)])
            self.assertEquals(r.status_code, 204)

            self.assertIn(
                ('open', channel['tracking_code']),
                UserActivity.query.filter_by(user=user.id).values('action', 'tracking_code'))


class TestEmail(base.RockPackTestCase):

    def _record_user_event(self, user, event_date):
        UserAccountEvent(
            event_date=event_date,
            event_type='login',
            event_value='',
            ip_address='',
            user_agent='',
            clientid='',
            username='',
            user=user.id,
        ).save()

    def test_email_registration(self):
        with self.app.test_client():
            self.app.test_request_context().push()

            from rockpack.mainsite.services.user import commands
            with patch('rockpack.mainsite.core.email.send_email') as send_email:
                user = self.create_test_user(date_joined=datetime(2100, 1, 2))
                commands.create_registration_emails(datetime(2100, 1, 1), datetime(2100, 1, 10))
                self.assertEquals(send_email.call_count, 1)
                assert user.email == send_email.call_args[0][0]
                assert 'Welcome to Rockpack' == send_email.call_args[0][1]
                assert 'Hi {}'.format(user.display_name) in send_email.call_args[0][2]
                #assert 'You are subscribed as {}'.format(user.email) in send_email.call_args[0][2]
                assert 'To ensure our emails reach your inbox please make sure to add {}'.format(
                    cgi.escape(app.config['DEFAULT_EMAIL_SOURCE'])) in send_email.call_args[0][2]

                user2 = self.create_test_user(date_joined=datetime(2100, 2, 2))
                commands.create_registration_emails(datetime(2100, 2, 1), datetime(2100, 2, 10))
                self.assertEquals(send_email.call_count, 2)
                assert 'Hi {}'.format(user2.display_name) in send_email.call_args[0][2]

                # Check that invalid email doesn't break
                self.create_test_user(date_joined=datetime(2100, 3, 2), email='xxx')
                # No email should be sent to user2 (with blank address)
                self.create_test_user(date_joined=datetime(2100, 3, 3), email='')

                commands.create_registration_emails(datetime(2100, 3, 1), datetime(2100, 3, 10))
                self.assertEquals(send_email.call_count, 3)

    @skip_unless_config('TEST_WELCOME_EMAIL')
    def test_email_registration_wo_patch(self):
        from rockpack.mainsite.services.user import commands
        with self.app.test_client():
            self.app.test_request_context().push()
            self.create_test_user(
                date_joined=datetime(2200, 1, 2),
                email=app.config['TEST_WELCOME_EMAIL']
            )
            commands.create_registration_emails(datetime(2200, 1, 1), datetime(2200, 1, 10))

    def _create_reactivation_email(self, user):
        # record an event 7 days ago and set inactivity window to now
        self._record_user_event(user, datetime.now() - timedelta(7))
        window = datetime.now() - timedelta(seconds=900), datetime.now()

        # populate users feed
        for n, i in VideoInstanceData():
            UserContentFeed(user=user.id, channel=i.channel, video_instance=i.id).save()
        for n, i in ChannelData():
            UserContentFeed(user=user.id, channel=i.id).save()

        # create reactivation email
        self.app.test_request_context().push()
        cron_cmds.create_reactivation_emails(*window)

        return window

    @patch('rockpack.mainsite.core.email.send_email')
    def test_email_reactivation(self, send_email):
        # check successful sending of email
        user = self.create_test_user()
        window = self._create_reactivation_email(user)
        self.assertEqual(send_email.call_count, 1)
        recipient, subject, body = send_email.call_args[0]
        self.assertEqual(recipient, user.email)
        self.assertEqual(subject, "What's trending in your Rockpack")
        self.assertIn('has added 2 videos to CHANNEL #3', body)
        self.assertIn('has added 1 videos to CHANNEL #4', body)
        self.assertIn('utm_medium=email', body)
        #open('temp.html', 'wb').write(body.encode('utf8'))

        # check that email isn't sent to active, bouncing, or unsubscribed users
        send_email.reset_mock()
        for update_user in (lambda u: self._record_user_event(u, datetime.now()),
                            lambda u: u.set_flag('bouncing'),
                            lambda u: u.set_flag('unsub1')):
            UserFlag.query.filter_by(user=user.id).delete()
            update_user(user)
            user.save()
            cron_cmds.create_reactivation_emails(*window)
            self.assertEqual(send_email.call_count, 0)

    @skip_unless_config('TEST_REACTIVATION_EMAIL')
    def test_email_reactivation_wo_patch(self):
        user = self.create_test_user(email=app.config['TEST_REACTIVATION_EMAIL'])
        self._create_reactivation_email(user)
