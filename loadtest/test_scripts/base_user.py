import sys
import os
import time
import random
import re
import urlparse
import uuid
from itertools import chain
import simplejson as json
import requests


sys.path.append(reduce(lambda d, _: os.path.dirname(d), xrange(3), os.path.abspath(__file__)))
try:
    from rockpack.mainsite import app
except ImportError:
    app = type('App', (object,), dict(config={}))


SERVER = app.config.get('LOADTEST_SERVER', 'http://127.0.0.1:5000')
DISCOVER_URL = app.config.get('LOADTEST_DISCOVER_URL', 'http://lb.us.rockpack.com/ws/')
CLIENT_AUTH_HEADER = app.config.get('CLIENT_AUTH_HEADER', ('Authorization', 'Basic YzhmZTVmNnJvY2s4NzNkcGFjazE5UTo='))


class BaseTransaction(object):

    def __init__(self):
        self.urls = {}
        self._process = None

    def run(self):
        self.custom_timers = {}
        if not self.urls:
            self.urls = self.get(DISCOVER_URL)
        if not self._process:
            self._process = self.process()
        try:
            sleep = self._process.next()
            if sleep is True:
                sleep = random.random()
            if sleep:
                time.sleep(sleep)
            return sleep
        except (AttributeError, StopIteration):
            self._process = None

    def request(self, url, method='get', params=None, data=None, headers=[], token=None):
        parsed_url = urlparse.urlparse(url)
        url = urlparse.urljoin(SERVER, parsed_url.path)
        headers = headers[:]
        headers.append(('Host', parsed_url.netloc))
        if token:
            headers.append(('Authorization', 'Bearer %s' % token))
        start = time.time()
        response = requests.request(method, url, params=params, data=data, headers=headers)
        service_name = method.upper() + '-' +\
            re.sub('/[\w-]{22,24}', '/X', parsed_url.path).strip('/').replace('/', '-')
        #assert str(service_name) not in self.custom_timers, self.custom_timers
        self.custom_timers[str(service_name)] = time.time() - start
        response.raise_for_status()
        try:
            return response.json()
        except json.scanner.JSONDecodeError:
            return response.text

    def get(self, url, params=None, headers=[], token=None):
        return self.request(url, params=params, headers=headers, token=token)

    def post(self, url, data, method='post', headers=[], token=None):
        headers.append(('Content-Type', 'application/json'))
        return self.request(url, data=json.dumps(data), method=method, headers=headers, token=token)

    def put(self, url, data, headers=[], token=None):
        return self.post(url, data, method='put', headers=headers, token=token)

    def register_user(self):
        s = uuid.uuid4().hex
        regdata = dict(username=s, password=s, email='%s@rockpack.com' % s, locale='en-us')
        credentials = self.post(self.urls['register'], regdata, headers=[CLIENT_AUTH_HEADER])
        self.token = credentials['access_token']
        self.urls['user'] = credentials['resource_url']
        userinfo = self.get(self.urls['user'], token=self.token)
        for key in 'subscriptions', 'channels', 'activity':
            self.urls[key] = userinfo[key]['resource_url']
        return userinfo

    def get_cat_ids(self):
        categories = self.get(self.urls['categories'])['categories']['items']
        return [c['id'] for c in chain(categories,
                *(c.get('sub_categories', []) for c in categories))]

    def test(self):
        i = 0
        while True:
            cont = self.run()
            print '# %d' % i
            i += 1
            for name, value in self.custom_timers.items():
                print '%s: %.5f secs' % (name, value)
            if not cont:
                break
        self.run()


class Transaction(BaseTransaction):
    pass
