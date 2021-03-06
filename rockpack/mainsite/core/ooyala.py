import os
from time import time
from datetime import datetime
from base64 import b64encode
from hashlib import sha256
from urlparse import urljoin
from collections import namedtuple
from flask import json
from wonder.common.sqs import background_on_sqs
from rockpack.mainsite import app, requests
from rockpack.mainsite.core.s3 import s3connection
from rockpack.mainsite.services.video.models import Video, VideoThumbnail


BASE_URL = 'https://api.ooyala.com'

Videolist = namedtuple('Videolist', 'video_count videos')


def _parse_datetime(dt):
    return datetime.strptime(dt[:19], '%Y-%m-%dT%H:%M:%S')


def _generate_signature(method, path, params, body=''):
    # See http://support.ooyala.com/developers/documentation/tasks/api_signing_requests.html
    head = app.config['OOYALA_SECRET'] + method.upper() + path
    for key, value in sorted(params.iteritems()):
        head += ('%s=%s' % (key, value)).encode('utf8')
    return b64encode(sha256(head + body).digest())[0:43]


def _ooyala_feed(feed, *resource, **kwargs):
    method = kwargs.pop('method', 'post' if 'data' in kwargs else 'get')
    path = '/'.join(('', 'v2', feed) + resource)
    params = dict(
        api_key=app.config['OOYALA_API_KEY'],
        expires=int(time()) + 60,
    )
    params.update(kwargs.pop('params', {}))
    params['signature'] = _generate_signature(method, path, params, kwargs.get('data', ''))
    response = requests.request(method, urljoin(BASE_URL, path), params=params, **kwargs)
    response.raise_for_status()
    return response.json()


def get_video_data(id, fetch_all_videos=True, fetch_metadata=False):
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
    update_thumbnails(video)
    if fetch_metadata:
        video.meta = _ooyala_feed('assets', id, 'metadata')
        video.category = video.meta.get('category', None)
    return Videolist(1, [video])


def update_thumbnails(video):
    preview_image = _ooyala_feed('assets', video.source_videoid, 'primary_preview_image')
    video.thumbnails = [
        VideoThumbnail(
            url=thumbnail['url'],
            width=thumbnail['width'],
            height=thumbnail['height'],
        )
        for thumbnail in preview_image['sizes']
    ]


def create_asset(s3path, metadata):
    # get metadata from s3
    chunk_size = 2 ** 23
    bucket = s3connection().get_bucket(app.config['VIDEO_S3_BUCKET'])
    key = bucket.get_key(s3path)
    if not key:
        app.logger.error('s3://%s/%s not found', bucket.name, s3path)
        return
    file_size = key.size
    file_name = os.path.basename(key.name)
    name = metadata.pop('title', None) or os.path.splitext(file_name)[0].capitalize()

    # check if asset already exists
    name_exists = "name='%s'" % name.replace("'", "\\'")
    assets = _ooyala_feed('assets', params=dict(where=name_exists, include='metadata'))
    if assets['items'] and assets['items'][0]['name'] == name:
        app.logger.warning('Asset already exists for "%s"', name)
        return

    # create asset on ooyala
    asset = dict(
        asset_type='video',
        file_name=file_name,
        name=name,
        file_size=file_size,
        chunk_size=chunk_size,
    )
    response = _ooyala_feed('assets', data=json.dumps(asset))
    assetid = response['embed_code']

    # set label and metadata
    labelname = metadata.pop('label', None)
    if labelname:
        idmap = dict((l['name'], l['id']) for l in _ooyala_feed('labels')['items'])
        if labelname in idmap:
            labelid = idmap[labelname]
        else:
            labelid = _ooyala_feed('labels', data=json.dumps(dict(name=labelname)))['id']
        _ooyala_feed('assets', assetid, 'labels', labelid, method='put')
    if metadata:
        _ooyala_feed('assets', assetid, 'metadata',
                     method='patch', data=json.dumps(metadata))

    # copy video data from s3 to ooyala
    range = -1, -1
    for upload_url in _ooyala_feed('assets', assetid, 'uploading_urls'):
        range = range[1] + 1, min(range[1] + chunk_size, file_size - 1)
        buf = key.get_contents_as_string(headers={'Range': 'bytes=%d-%d' % range})
        response = requests.put(upload_url, buf)
        response.raise_for_status()
        assert response.status_code == 204
    _ooyala_feed('assets', assetid, 'upload_status',
                 method='put', data=json.dumps(dict(status='uploaded')))

    return assetid


@background_on_sqs
def create_asset_in_background(s3path, metadata):
    try:
        create_asset(s3path, metadata)
    except Exception as e:
        if hasattr(e, 'response') and 'error: duplicate' in e.response.content:
            app.logger.error('Duplicate content: "%s": %s', s3path, e.response.content)
        else:
            raise
