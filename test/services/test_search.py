import json
from rockpack.mainsite.core.dbapi import db
from ..base import RockPackTestCase
from ..fixtures import ChannelData, VideoData, UserData
from ..test_decorators import skip_unless_config, skip_if_dolly


class SearchTestCase(RockPackTestCase):

    def _search(self, type, query):
        with self.app.test_client() as client:
            r = client.get('/ws/search/%s/' % type, query_string=dict(q=query))
            self.assertEquals(200, r.status_code)
            result = json.loads(r.data)[type]
        return result

    @skip_unless_config('ELASTICSEARCH_URL')
    def test_search_channel_by_username(self):
        with self.app.test_request_context():
            owner = self.create_test_user()
            self.wait_for_es()

            channels = self._search('channels', owner.username)
            self.assertEquals(channels['total'], 1)
            self.assertEqual(channels['items'][0]['owner']['id'], owner.id)

    @skip_unless_config('ELASTICSEARCH_URL')
    def test_search_channel_by_video_title(self):
        with self.app.test_request_context():
            owner = self.create_test_user()
            channel, = owner.channels
            channel.add_videos([VideoData.video1.id])
            db.session.commit()
            self.wait_for_es()

            channels = self._search('channels', VideoData.video1.title)
            self.assertGreater(channels['total'], 0)
            self.assertIn(channel.id, [c['id'] for c in channels['items']])
            self.assertGreater(channels['items'][0]['videos']['total'], 0)


@skip_if_dolly
class CompleteTestCase(RockPackTestCase):

    def _complete(self, type, query):
        with self.app.test_client() as client:
            r = client.get('/ws/complete/%s/' % type, query_string=dict(q=query))
            self.assertEquals(200, r.status_code)
            self.assertEquals(r.data[:19], 'window.google.ac.h(')
            data = r.data[19:-1]
            term, result, meta = json.loads(data)
            self.assertGreater(len(result), 0)
        return result

    def test_complete_videos(self):
        prefix = 'th'
        result = self._complete('videos', prefix)
        
        for r in result:
            self.assertEquals(r[0][:len(prefix)], prefix)

    def test_complete_users(self):
        username = UserData.test_user_a.username
        result = self._complete('users', username[:2])
        self.assertIn(username, [t for t, m in result])

    def test_complete_channels(self):
        channel_title = ChannelData.channel1.title
        result = self._complete('channels', channel_title[:2])
        self.assertIn(channel_title, [t for t, m in result])

    def test_complete_all(self):
        self.create_test_user()     # create test user with channel
        self.app.config['COMPLETE_ALL_TYPES_THRESHOLD'] = 0
        result = self._complete('all', 'test')
        terms = zip(*result)[0]
        data = zip(*result)[1]
        self.assertGreater(terms, 3)
        # users first
        self.assertEquals(terms[0], UserData.test_user_a.username) # test_user_1
		# data type for user
        
        self.assertEquals(data[0][0], 'user')
        self.assertEquals(data[0][1], UserData.test_user_a.id)
        self.assertEquals(data[0][2], UserData.test_user_a.username)
        # then channels
        self.assertRegexpMatches(terms[1], '^test_[0-9a-f]{32}$')
        # then some videos
        self.assertEquals(terms[-1][:4], 'test')
