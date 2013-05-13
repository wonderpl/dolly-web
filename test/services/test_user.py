import json
from test import base
from test.fixtures import ChannelData, VideoInstanceData
from test.test_helpers import get_auth_header
from test.test_helpers import get_client_auth_header
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

    def test_fullname_toggle(self):
        with self.app.test_client() as client:
            new_user = self.create_test_user()

            r = client.get('/ws/{}/'.format(new_user.id),
                content_type='application/json',
                headers=[get_auth_header(new_user.id)])
            old_data = json.loads(r.data)

            client.put('/ws/{}/display_fullname/'.format(new_user.id),
                data=json.dumps(False),
                content_type='application/json',
                headers=[get_auth_header(new_user.id)])

            r = client.get('/ws/{}/'.format(new_user.id),
                content_type='application/json',
                headers=[get_auth_header(new_user.id)])
            new_data = json.loads(r.data)

            self.assertNotEquals(old_data['display_name'], new_data['display_name'])
            self.assertEquals(new_data['username'], new_data['display_name'])

    def test_password_change(self):
        with self.app.test_client() as client:
            new_user = self.create_test_user()
            r = client.put('/ws/{}/{}/'.format(new_user.id, 'password'),
                    data=json.dumps(dict(old='password', new='imbatman')),
                    content_type='application/json',
                    headers=[get_auth_header(new_user.id)])

            creds = json.loads(r.data)

            r = client.post('/ws/token/',
                    headers=[get_client_auth_header()],
                    data=dict(refresh_token=creds['refresh_token'],
                        grant_type='refresh_token'))

            new_creds = json.loads(r.data)

            self.assertEquals('Bearer', new_creds['token_type'], 'token type should be Bearer')
            self.assertEquals(new_creds['refresh_token'], creds['refresh_token'], 'refresh tokens should be the same')
            self.assertNotEquals(new_creds['access_token'],
                creds['access_token'],
                'old access token should not be the same at the new one')

    def test_failed_password_length(self):
        with self.app.test_client() as client:
            new_user = self.create_test_user()
            r = client.put('/ws/{}/{}/'.format(new_user.id, 'password'),
                    data=json.dumps(dict(old='password', new='4char')),
                    content_type='application/json',
                    headers=[get_auth_header(new_user.id)])

            data = json.loads(r.data)
            self.assertEquals(data['message'], ["Field must be at least 6 characters long."])

    def test_failed_old_password(self):
        with self.app.test_client() as client:
            new_user = self.create_test_user()
            r = client.put('/ws/{}/{}/'.format(new_user.id, 'password'),
                    data=json.dumps(dict(old='wrong', new='6chars')),
                    content_type='application/json',
                    headers=[get_auth_header(new_user.id)])

            data = json.loads(r.data)
            self.assertEquals(data['message'], ["Old password is incorrect."])

    def test_failed_password(self):
        with self.app.test_client() as client:
            new_user = self.create_test_user()
            r = client.put('/ws/{}/{}/'.format(new_user.id, 'password'),
                    data=json.dumps({}),
                    content_type='application/json',
                    headers=[get_auth_header(new_user.id)])

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
                    headers=[get_auth_header(new_user.id)])

                self.assertEquals(r.status_code, 204, "{} - {}".format(field, r.data))

            user = User.query.get(new_user.id)
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
