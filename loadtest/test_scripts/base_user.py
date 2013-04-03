import time
import re
import urlparse
import uuid
from itertools import chain
import simplejson as json
import requests


SERVER = 'http://localhost:5000'
DISCOVER_URL = 'http://lb.us.rockpack.com/ws/'
CLIENT_AUTH_HEADER = 'Authorization', 'Basic YzhmZTVmNnJvY2s4NzNkcGFjazE5UTo='


class BaseTransaction(object):

    def __init__(self):
        self.custom_timers = {}
        self.urls = {}

    def run(self):
        self.urls = self.get(DISCOVER_URL)
        try:
            self._run()
        except Exception, e:
            self.custom_timers['errors'] = 1
            import logging, base64, struct
            try:
                userid = base64.urlsafe_b64encode(struct.unpack('>Hd16s16s', base64.urlsafe_b64decode(str(self.token)[40:]))[2])[:-2]
            except:
                userid = self.token
            logging.exception('%s %s', e.response.url if hasattr(e, 'response') else e, userid)
            raise

    def request(self, url, method='get', params=None, data=None, headers=[], token=None):
        parsed_url = urlparse.urlparse(url)
        url = urlparse.urljoin(SERVER, parsed_url.path)
        headers.append(('Host', parsed_url.netloc))
        if token:
            headers.append(('Authorization', 'Bearer %s' % token))
        start = time.time()
        #print url, headers
        response = requests.request(method, url, params=params, data=data, headers=headers)
        service_name = method.upper() + '-' +\
            re.sub('/[\w-]{22,24}', '/X', parsed_url.path).strip('/').replace('/', '-')
        self.custom_timers[str(service_name)] = time.time() - start
        response.raise_for_status()
        try:
            return response.json()
        except json.scanner.JSONDecodeError:
            return None

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
        self.urls.setdefault('user', credentials['resource_url'])
        userinfo = self.get(self.urls['user'], token=self.token)
        for key, value in userinfo.items():
            try:
                self.urls.setdefault(key, value['resource_url'])
            except (TypeError, KeyError):
                pass
        return userinfo

    def get_cat_ids(self):
        categories = self.get(self.urls['categories'])['categories']['items']
        return [c['id'] for c in chain(categories,
                *(c.get('sub_categories', []) for c in categories))]

    def print_times(self):
        for name, value in self.custom_timers.items():
            print '%s: %.5f secs' % (name, value)
