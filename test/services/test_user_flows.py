import uuid
import json
import random
import urllib
import urlparse
from itertools import chain
from flask import Flask
import rockpack.mainsite
from ..base import RockPackTestCase
from ..test_helpers import get_client_auth_header


class BaseUserTestCase(RockPackTestCase):

    def setUp(self):
        super(BaseUserTestCase, self).setUp()
        # This nasty hack of copying the main app is so that we can re-init
        # with the new subdomains and ensure that the additional routes are
        # added and will work with the test client.
        self.old_app = rockpack.mainsite.app
        self.app = rockpack.mainsite.app = Flask('rockpack.mainsite')
        rockpack.mainsite.configure()
        rockpack.mainsite.app.config.update(
            SERVER_NAME='rockpack.com',
            SECURE_SUBDOMAIN='secure',
            DEFAULT_SUBDOMAIN='lb.us',
            API_SUBDOMAIN='api',
        )
        rockpack.mainsite.init_app()
        self.default_base_url = 'http://%(DEFAULT_SUBDOMAIN)s.%(SERVER_NAME)s' % self.app.config
        self.discovery_url = self.default_base_url + '/ws/'
        self.client = self.app.test_client()

        if self.app.config.get('ELASTICSEARCH_URL'):
            from rockpack.mainsite.core.es import helpers

            i = helpers.Indexing()
            i.create_all_indexes(rebuild=True)
            i.create_all_mappings()

            i = helpers.DBImport()
            i.import_channels()
            i.import_videos()
            i.import_users()

    def tearDown(self):
        rockpack.mainsite.app = self.old_app
        super(BaseUserTestCase, self).tearDown()

    def request(self, url, method='get', params=None, data=None, headers=[], token=None):
        parsed_url = urlparse.urlparse(url)
        response = self.client.open(
            method=method.upper(),
            path=parsed_url.path,
            base_url=urlparse.urljoin(url, '/'),
            query_string=params and urllib.urlencode(params),
            data=data,
            content_type=dict(headers).get('Content-Type'),
            headers=headers + ([('Authorization', 'Bearer %s' % token)] if token else []),
        )
        self.assertIn(response.status_code, (200, 201, 204),
                      msg='%s responded with %d' % (url, response.status_code))
        try:
            return json.loads(response.data)
        except ValueError:
            return response.data

    def get(self, url, params=None, headers=[], token=None):
        return self.request(url, params=params, headers=headers, token=token)

    def post(self, url, data, method='post', headers=[], token=None):
        headers.append(('Content-Type', 'application/json'))
        return self.request(url, data=json.dumps(data), method=method, headers=headers, token=token)

    def put(self, url, data, headers=[], token=None):
        return self.post(url, data, method='put', headers=headers, token=token)

    @property
    def urls(self):
        if not hasattr(self, '_urls'):
            self._urls = self.get(self.discovery_url)
        return self._urls

    def register_user(self):
        s = uuid.uuid4().hex
        regdata = dict(username=s, password=s, email='%s@rockpack.com' % s, locale='en-us')
        credentials = self.post(self.urls['register'], data=regdata, headers=[get_client_auth_header()])
        self.token = credentials['access_token']
        self._urls['user'] = credentials['resource_url']
        userinfo = self.get(self._urls['user'], token=self.token)
        for key in 'subscriptions', 'channels', 'activity':
            self._urls[key] = userinfo[key]['resource_url']
        return userinfo

    def get_cat_ids(self):
        categories = self.get(self.urls['categories'])['categories']['items']
        return [c['id'] for c in chain(categories,
                *(c.get('sub_categories', []) for c in categories))]


class BrowsingUserTestCase(BaseUserTestCase):

    def test_flow(self):
        """
        - Register a new user
        - Browse all categories
        - For every channel...
        - Watch the videos
        - Post the view activity
        """
        viewed_videos = []
        self.register_user()

        self.wait_for_es()

        for cat_id in self.get_cat_ids():
            popular_channels = self.get(self.urls['popular_channels'], dict(category=cat_id))
            for channel in popular_channels['channels']['items']:
                if not channel['category']:
                    continue
                channel_detail = self.get(channel['resource_url'])
                for video in channel_detail['videos']['items']:
                    self.post(self.urls['activity'],
                              dict(action='view', video_instance=video['id']),
                              token=self.token)
                    viewed_videos.append(video['id'])

        # confirm activity was recorded
        self.assertGreater(len(viewed_videos), 0)
        activity = self.get(self.urls['activity'], token=self.token)
        #self.assertListEqual(viewed_videos, activity['recently_viewed'])
        self.assertEquals([], list(set(viewed_videos).difference(activity['recently_viewed'])))


class SubscribingUserTestCase(BaseUserTestCase):

    def test_flow(self):
        """
        - Register new user
        - Get first channel from popular channels for each category
        - Subscribe to channel
        """
        subscribed_channels = []
        self.register_user()
        self.wait_for_es()
        for cat_id in self.get_cat_ids():
            popular_channels = self.get(self.urls['popular_channels'], dict(category=cat_id))
            if popular_channels['channels']['total'] == 0:
                continue
            channel = popular_channels['channels']['items'][0]
            if channel['id'] not in subscribed_channels:
                self.post(self.urls['subscriptions'], channel['resource_url'], token=self.token)
                subscribed_channels.append(channel['id'])

        self.assertGreater(len(subscribed_channels), 0)
        subscriptions = self.get(self.urls['subscriptions'], token=self.token)
        self.assertItemsEqual(subscribed_channels, [c['id'] for c in subscriptions['channels']['items']])
        videos = self.get(self.urls['subscriptions'] + 'recent_videos/', token=self.token)
        self.assertGreater(len(videos['videos']['items']), 0)
        self.assertIn(videos['videos']['items'][0]['channel']['id'], subscribed_channels)


class CuratingUserTestCase(BaseUserTestCase):

    def test_flow(self):
        """
        - Register new user
        - Choose random search term
        - Search for videos
        - Record select activity for first 5 video results
        - Get cover art
        - Create new channel
        - Add the selected videos to new channel
        - Verify channel contents
        """
        self.register_user()

        # Select first search term suggestion
        search_terms = self.get(self.urls['video_search_terms'], dict(q='tes'))
        search_term = json.loads(search_terms[19:-1])[1][0][0]

        # Get first 5 results for search term
        params = dict(q=search_term, size=5)
        videos = self.get(self.urls['video_search'], params=params)['videos']['items']
        # Might not get 5 results because some might be restricted
        self.assertGreater(len(videos), 2)

        # Record selection
        selected_videos = []
        selected_source_ids = []
        for i, video in enumerate(videos):
            # Deliberately don't select the first video, to test if record created later
            if i:
                self.post(self.urls['activity'],
                          dict(action='select', video_instance=video['id']),
                          token=self.token)
            selected_videos.append(video['id'])
            selected_source_ids.append(video['video']['source_id'])

        # Create channel
        category = random.choice(self.get_cat_ids())
        cover = random.choice(self.get(self.urls['cover_art'])['cover_art']['items'])['cover_ref']
        chdata = dict(
            title=uuid.uuid4().hex[:20],
            category=category,
            cover=cover,
            description='test',
            public=True,
        )
        channel = self.post(self.urls['channels'], chdata, token=self.token)
        self.wait_for_es()
        self.put(channel['resource_url'] + 'videos/', selected_videos, token=self.token)
        self.wait_for_es()

        # Verify results
        channels = self.get(self.urls['channel_search'], dict(q=chdata['title']))['channels']
        self.assertEquals(channels['total'], 1, 'expected total=1, got %r' % channels)
        videos = self.get(channels['items'][0]['resource_url'])['videos']
        source_ids = [v['video']['source_id'] for v in videos['items']]
        self.assertEquals([], list(set(selected_source_ids).difference(source_ids)))
