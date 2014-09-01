import re
import uuid
from urlparse import urlparse
from flask import json
from jinja2.filters import do_striptags
from mock import patch
from rockpack.mainsite import app
from rockpack.mainsite.services.video.models import Channel
from rockpack.mainsite.services.user.models import UserNotification
from rockpack.mainsite.services.oauth.models import ExternalFriend, ExternalToken
from test import base
from ..test_decorators import skip_if_dolly, skip_unless_config, patch_send_email
from ..test_helpers import get_auth_header, get_client_auth_header
from ..fixtures import ChannelData, VideoInstanceData, UserData


class TestShare(base.RockPackTestCase):

    def _get_share_link(self, userid, object_type, object_id):
        userid = userid or self.create_test_user().id
        with self.app.test_client() as client:
            r = client.post(
                '/ws/share/link/',
                data=json.dumps({
                    'object_type': object_type,
                    'object_id': object_id
                }),
                content_type='application/json',
                headers=[get_auth_header(userid)])

            self.assertEquals(r.status_code, 201, r.data)
            data = json.loads(r.data)
            self.assertIn('/s/', data['resource_url'])
            self.assertEquals(data['resource_url'], r.headers['Location'])
        return data

    def test_channel_share_link(self):
        data = self._get_share_link(None, 'channel', ChannelData.channel1.id)
        self.assertIn('pack', data['message'])

        # Confirm link redirects to channel
        with self.app.test_client() as client:
            r = client.get(urlparse(data['resource_url']).path)
            self.assertIn(ChannelData.channel1.id, r.headers['Location'])

    def test_video_share_link(self):
        app.config['SHARE_MESSAGE_MAP']['video_instance']['message'] =\
            '"{0[title]}" {0[content_owner]}'

        data = self._get_share_link(None, 'video_instance', VideoInstanceData.video_instance3.id)

        self.assertEquals(data['message'], '"Another 48hrs" @test123')

        # Confirm link redirects to channel
        with self.app.test_client() as client:
            r = client.get(urlparse(data['resource_url']).path)
            self.assertIn('/%s/' % VideoInstanceData.video_instance3.channel, r.headers['Location'])
            self.assertIn('video=%s' % VideoInstanceData.video_instance3.id, r.headers['Location'])

    @skip_if_dolly
    def test_search_video_share_link(self):
        self.app.test_request_context().push()
        userid = self.create_test_user().id
        with self.app.test_client() as client:
            r = client.get('/ws/search/videos/', query_string='size=1')
            video = json.loads(r.data)['videos']['items'][0]['id']
        data = self._get_share_link(userid, 'video_instance', video)

        with self.app.test_client() as client:
            r = client.get(urlparse(data['resource_url']).path)
            self.assertEquals(r.status_code, 302)
            channelid, videoid = re.match(r'.*/([^/]+)/\?.*video=(.+)', r.headers['Location']).groups()

        # try sharing again
        self._get_share_link(userid, 'video_instance', video)

        # Confirm shared channel & video was from user's favourites
        favourites = Channel.query.filter_by(owner=userid, favourite=True).one()
        self.assertEquals(channelid, favourites.id)
        self.assertEquals([videoid], [v.id for v in favourites.video_instances])

    def test_passthru_share_params(self):
        data = self._get_share_link(None, 'video_instance', VideoInstanceData.video_instance2.id)

        self.app.config['SHARE_REDIRECT_PASSTHROUGH_PARAMS'] = ['umts']

        # Confirm link redirects to channel
        with self.app.test_client() as client:
            r = client.get(urlparse(data['resource_url']).path + '?umts=foo')
            self.assertIn('umts=foo', r.headers['Location'])

        self.app.config['SHARE_REDIRECT_PASSTHROUGH_PARAMS'] = []

    @patch_send_email()
    def test_reverse_relation_for_late_registered_user(self, send_email):
        recipient_email = 'noreply+unregistered_user@wonderpl.com'

        # Send and email then register emailed user

        with self.app.test_client() as client:
            sender = self.create_test_user()
            r = client.post(
                '/ws/share/email/',
                data=json.dumps(dict(
                    object_type='channel',
                    object_id=ChannelData.channel1.id,
                    external_uid=recipient_email,
                    external_system='email',
                    email=recipient_email,
                )),
                content_type='application/json',
                headers=[get_auth_header(sender.id)])
            self.assertEquals(r.status_code, 204, r.data)

        with self.app.test_request_context():
            with self.app.test_client() as client:
                r = client.post(
                    '/ws/register/',
                    headers=[get_client_auth_header()],
                    data=dict(
                        username=uuid.uuid4().hex,
                        password='barbar',
                        first_name='foo',
                        last_name='bar',
                        date_of_birth='2000-01-01',
                        locale='en-us',
                        email=recipient_email))

                user_id = json.loads(r.data)['user_id']

        ExternalFriend.query.filter(
            ExternalFriend.user == user_id,
            ExternalFriend.email == sender.email
        ).one()

    @patch_send_email()
    def test_reverse_relation_for_registered_user(self, send_email):
        # Email registered user

        recipient_email = 'noreply+registered_user@wonderpl.com'

        with self.app.test_request_context():
            with self.app.test_client() as client:
                r = client.post(
                    '/ws/register/',
                    headers=[get_client_auth_header()],
                    data=dict(
                        username=uuid.uuid4().hex,
                        password='barbar',
                        first_name='foo',
                        last_name='bar',
                        date_of_birth='2000-01-01',
                        locale='en-us',
                        email=recipient_email))

                user_id = json.loads(r.data)['user_id']

        with self.app.test_client() as client:
            sender = self.create_test_user()
            r = client.post(
                '/ws/share/email/',
                data=json.dumps(dict(
                    object_type='channel',
                    object_id=ChannelData.channel1.id,
                    external_uid=recipient_email,
                    external_system='email',
                    email=recipient_email,
                )),
                content_type='application/json',
                headers=[get_auth_header(sender.id)])
            self.assertEquals(r.status_code, 204, r.data)

        ExternalFriend.query.filter(
            ExternalFriend.user == user_id,
            ExternalFriend.email == sender.email
        ).one()

    @patch_send_email()
    def test_share_push_notification(self, send_email):
        user = self.create_test_user()
        ExternalToken(
            user=user.id,
            external_system='apns',
            external_token='xxx',
            external_uid=user.id,
        ).save()
        with self.app.test_client() as client:
            r = client.post(
                '/ws/share/email/',
                data=json.dumps(dict(
                    object_type='video_instance',
                    object_id=VideoInstanceData.video_instance1.id,
                    email=user.email,
                    external_system='email',
                    external_uid=user.email,
                )),
                content_type='application/json',
                headers=[get_auth_header(UserData.test_user_a.id)])
            self.assertEquals(r.status_code, 204, r.data)

        from rockpack.mainsite.services.user import commands
        import apnsclient
        with patch.object(apnsclient.APNs, 'send', lambda o, m: apnsclient.Result(m)):
            message = commands.send_push_notifications(user).message
            self.assertIn('shared a video with you', message.alert['loc-key'])
            self.assertIn(VideoInstanceData.video_instance1.id, message.payload['url'])
            self.assertGreater(message.badge, 0)

    @patch_send_email()
    def test_channel_share_email(self, send_email):
        with self.app.test_client() as client:
            userid = self.create_test_user().id
            recipient = UserData.test_user_a.email
            r = client.post(
                '/ws/share/email/',
                data=json.dumps(dict(
                    object_type='channel',
                    object_id=ChannelData.channel1.id,
                    email=recipient,
                    external_system='email',
                    external_uid='123',
                )),
                content_type='application/json',
                headers=[get_auth_header(userid)])
            self.assertEquals(r.status_code, 204, r.data)

        self.assertEquals(send_email.call_count, 1)
        self.assertEquals(send_email.call_args[0][0], recipient)
        if self.app.config.get('DOLLY'):
            self.assertIn('subscribed as %s.' % recipient, do_striptags(send_email.call_args[0][1]))

        notifications = UserNotification.query.filter_by(
            user=UserData.test_user_a.id, message_type='channel_shared')
        message = json.loads(notifications.value('message'))
        self.assertEquals(message['user']['id'], userid)
        self.assertEquals(message['channel']['id'], ChannelData.channel1.id)

        with self.app.test_client() as client:
            r = client.get(
                '/ws/%s/friends/' % userid,
                query_string='share_filter=true',
                headers=[get_auth_header(userid)])
            self.assertEquals(r.status_code, 200, r.data)
            friends = json.loads(r.data)['users']['items']
            self.assertIn(('email', recipient),
                          [(f['external_system'], f['email']) for f in friends])

    @patch_send_email()
    def test_video_share_email(self, send_email):
        with self.app.test_client() as client:
            userid = self.create_test_user(avatar='avatar').id
            recipient = 'noreply+unittest@rockpack.com'
            r = client.post(
                '/ws/share/email/',
                data=json.dumps(dict(
                    object_type='video_instance',
                    object_id=VideoInstanceData.video_instance1.id,
                    email=recipient,
                )),
                content_type='application/json',
                headers=[get_auth_header(userid)])
            self.assertEquals(r.status_code, 204, r.data)

        self.assertEquals(send_email.call_count, 1)
        self.assertEquals(send_email.call_args[0][0], recipient)

    @skip_unless_config('TEST_SHARE_EMAIL')
    def test_share_email_wo_patch(self):
        with self.app.test_client() as client:
            userid = self.create_test_user(avatar='avatar').id
            for object_type, object_id in [
                    ('channel', ChannelData.channel1.id),
                    ('video_instance', VideoInstanceData.video_instance1.id)]:
                r = client.post(
                    '/ws/share/email/',
                    data=json.dumps(dict(
                        object_type=object_type,
                        object_id=object_id,
                        email=app.config['TEST_SHARE_EMAIL'],
                    )),
                    content_type='application/json',
                    headers=[get_auth_header(userid)])
                self.assertEquals(r.status_code, 204, r.data)
