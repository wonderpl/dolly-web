import json
import uuid
import cgi
from datetime import datetime
from test import base
from mock import patch
from test.fixtures import ChannelData, VideoData, VideoInstanceData
from test.test_helpers import get_auth_header
from test.test_helpers import get_client_auth_header
from rockpack.mainsite import app
from rockpack.mainsite.services.video.models import Channel
from rockpack.mainsite.services.oauth.api import ExternalUser
from rockpack.mainsite.services.oauth.models import ExternalToken, ExternalFriend
from rockpack.mainsite.services.user.models import User, UserActivity, UserNotification, Subscription
from rockpack.mainsite.services.user import commands as cron_cmds


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

            UserNotification(
                user=user.id,
                message_type='subscribed',
                message=json.dumps(_notification_data(user))
            ).save()

            def _new_send(obj, message):
                return message.payload

            import apnsclient
            from rockpack.mainsite.services.user.commands import send_push_notification
            with patch.object(apnsclient.APNs, 'send', _new_send):
                message = send_push_notification(user)
                self.assertEquals(user.display_name, message['aps']['alert']['loc-args'][0])
                self.assertEquals(1, message['aps']['badge'])


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

    def test_content_feed(self):
        if not self.app.config.get('ELASTICSEARCH_URL'):
            return
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

            # Check videos from channel1 are present and aggregated
            self.assertIn(c1instances[0].id, itemids)
            agg = [a for a in data['aggregations'].values() if a['type'] == 'video'][0]
            self.assertEquals(agg['count'], len(c1instances))

            # Check stars on cover video
            cover = [i for i in data['items'] if i['id'] == agg['covers'][0]][0]
            self.assertEquals(cover['video']['star_count'], 3)
            self.assertItemsEqual([u['id'] for u in cover['starring_users']], [user1, user2, user3])

            # Check that new channels from friend and from subscription owner are present
            self.assertNotIn(u2old, itemids)
            self.assertIn(u2new, itemids)
            self.assertIn(u3new, itemids)

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
            user = self.create_test_user()
            video_instance = VideoInstanceData.video_instance1
            owner = Channel.query.get(video_instance.channel).owner
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
                user=owner, message_type='starred').one()
            message = json.loads(notification.message)
            self.assertEquals(message['user']['id'], user.id)
            self.assertEquals(message['video']['id'], video_instance.id)

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
                assert 'Hi {}'.format(user.username) in send_email.call_args[0][2]
                assert 'You are subscribed as {}'.format(user.email) in send_email.call_args[0][2]
                assert 'To ensure our emails reach your inbox please make sure to add {}'.format(
                    cgi.escape(app.config['DEFAULT_EMAIL_SOURCE'])) in send_email.call_args[0][2]

                user2 = self.create_test_user(date_joined=datetime(2100, 2, 2))
                commands.create_registration_emails(datetime(2100, 2, 1), datetime(2100, 2, 10))
                self.assertEquals(send_email.call_count, 2)
                assert 'Hi {}'.format(user2.username) in send_email.call_args[0][2]

                # Check that invalid email doesn't break
                self.create_test_user(date_joined=datetime(2100, 3, 2), email='xxx')
                # No email should be sent to user2 (with blank address)
                self.create_test_user(date_joined=datetime(2100, 3, 3), email='')

                commands.create_registration_emails(datetime(2100, 3, 1), datetime(2100, 3, 10))
                self.assertEquals(send_email.call_count, 3)

    if app.config.get('TEST_WELCOME_EMAIL'):
        def test_email_registration_wo_patch(self):
            from rockpack.mainsite.services.user import commands
            with self.app.test_client():
                self.app.test_request_context().push()
                self.create_test_user(
                    date_joined=datetime(2200, 1, 2),
                    email=app.config['TEST_WELCOME_EMAIL']
                )
                commands.create_registration_emails(datetime(2200, 1, 1), datetime(2200, 1, 10))
