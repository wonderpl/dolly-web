from time import time
from datetime import datetime
from base64 import b64encode
from hashlib import sha256
from urlparse import urljoin
from collections import namedtuple
from rockpack.mainsite import app, requests
from rockpack.mainsite.services.video.models import Video, VideoThumbnail


BASE_URL = 'https://cdn-api.ooyala.com'

Videolist = namedtuple('Videolist', 'video_count videos')


def _parse_datetime(dt):
    return datetime.strptime(dt[:19], '%Y-%m-%dT%H:%M:%S')


def _generate_signature(method, path, params, body=''):
    # See http://support.ooyala.com/developers/documentation/tasks/api_signing_requests.html
    head = app.config['OOYALA_SECRET'] + method.upper() + path
    for key, value in sorted(params.iteritems()):
        head += key + '=' + str(value)
    return b64encode(sha256(head + body).digest())[0:43]


def _ooyala_feed(feed, id, *resource):
    path = '/'.join(('', 'v2', feed, id) + resource)
    params = dict(
        api_key=app.config['OOYALA_API_KEY'],
        expires=int(time()) + 60,
    )
    params['signature'] = _generate_signature('get', path, params)
    response = requests.get(urljoin(BASE_URL, path), params=params)
    response.raise_for_status()
    return response.json()


def get_video_data(id, fetch_all_videos=True):
    """Return video data from youtube api as playlist of one."""
    data = _ooyala_feed('assets', id)
    video = Video(
        source_videoid=data['embed_code'],
        source_listid=None,
        source_username=None,
        date_published=_parse_datetime(data['updated_at']),
        title=data['name'],
        duration=data['duration'] / 1000,
    )
    video.source_date_uploaded = _parse_datetime(data['created_at'])
    video.restricted = bool(data['time_restrictions'])
    for thumbnail in _ooyala_feed('assets', id, 'primary_preview_image')['sizes']:
        video.thumbnails.append(
            VideoThumbnail(
                url=thumbnail['url'],
                width=thumbnail['width'],
                height=thumbnail['height']))
    return Videolist(1, [video])
