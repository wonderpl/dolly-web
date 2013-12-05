from datetime import datetime
from collections import namedtuple
from ooyala_api import OoyalaAPI
from rockpack.mainsite import app
from rockpack.mainsite.services.video.models import Video, VideoThumbnail


Videolist = namedtuple('Videolist', 'video_count videos')


def _parse_datetime(dt):
    return datetime.strptime(dt[:19], '%Y-%m-%dT%H:%M:%S')


def _ooyala_feed(feed, id, *resource):
    api = OoyalaAPI(app.config['OOYALA_API_KEY'], app.config['OOYALA_SECRET'])
    return api.get('/'.join((feed, id) + resource))


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
