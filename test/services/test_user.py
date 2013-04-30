import json
from test import base
from test.fixtures import ChannelData, VideoInstanceData
from test.test_helpers import get_auth_header
from rockpack.mainsite.services.video.models import Channel
from rockpack.mainsite.services.user.models import User, UserActivity, UserNotification
from rockpack.mainsite.services.user.commands import create_new_notifications


class TestProfileEdit(base.RockPackTestCase):

    def test_change_username(self):
        with self.app.test_client() as client:
            existing_user = self.create_test_user()

            new_user = self.create_test_user()
            r = client.put(
                '/ws/{}/username/'.format(new_user.id),
                data=json.dumps(existing_user.username),
                content_type='application/json',
                headers=[get_auth_header(new_user.id)])

            data = json.loads(r.data)
            self.assertEquals(r.status_code, 400)
            self.assertEquals(['"{}" already taken.'.format(existing_user.username)], data['message'])
            assert 'suggested_username' in data

            r = client.put(
                '/ws/{}/username/'.format(new_user.id),
                data=json.dumps('lemonademan'),
                content_type='application/json',
                headers=[get_auth_header(new_user.id)])

            self.assertEquals(r.status_code, 204)

    def test_other_fields(self):
        with self.app.test_client() as client:
            new_user = self.create_test_user()
            field_map = {
                "first_name": 'James',
                "last_name": 'Hong',
                "email": 'bigtrouble@littlechina.com',
                "password": 'lopanisgod',
                "locale": 'en-us',
                "gender": "m",
                "date_of_birth": '1901-01-01'}

            for field, value in field_map.iteritems():
                r = client.put(
                    '/ws/{}/{}/'.format(new_user.id, field),
                    data=json.dumps(value),
                    content_type='application/json',
                    headers=[get_auth_header(new_user.id)])

                self.assertEquals(r.status_code, 204, "{} - {}".format(field, r.data))

            user = User.query.get(new_user.id)
            self.assertEquals(user.check_password(field_map['password']), True)
            self.assertEquals(field_map['locale'], user.locale)
            self.assertEquals(field_map['email'], user.email)
            self.assertEquals(field_map['gender'], user.gender)
            self.assertEquals(field_map['last_name'], user.last_name)
            self.assertEquals(field_map['first_name'], user.first_name)
            self.assertEquals(field_map['date_of_birth'], user.date_of_birth.strftime("%Y-%m-%d"))

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

            create_new_notifications()
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

            create_new_notifications()
            notification = UserNotification.query.filter_by(
                user=owner, message_type='starred').one()
            message = json.loads(notification.message)
            self.assertEquals(message['user']['id'], user.id)
            self.assertEquals(message['video']['id'], video_instance.id)
