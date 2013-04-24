import logging
from collections import namedtuple
import gdata.youtube
from rockpack.mainsite import app, requests
from rockpack.mainsite.services.video.models import Video, VideoThumbnail, VideoRestriction


log = logging.getLogger(__name__)


PushConfig = namedtuple('PushConfig', 'hub topic')
Playlist = namedtuple('Playlist', 'title video_count videos push_config')
Videolist = namedtuple('Videolist', 'video_count videos')


def _youtube_feed(feed, id, params={}):
    """Get youtube feed data as json"""
    url = 'http://gdata.youtube.com/feeds/api/%s/%s' % (feed, id)
    params = dict(v=2, alt='json', **params)
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
    except Exception, e:
        if hasattr(e, 'response'):
            log.error('youtube request failed (%d): %s',
                      e.response.status_code, e.response.text)
        raise
    if isinstance(response.json, dict):
        return response.json
    return response.json()


def _get_atom_video_data(youtube_data, playlist=None):
    def get_category(categories):
        for category in categories:
            if category.scheme.endswith('categories.cat'):
                return category.text
    media = youtube_data.media
    video = Video(
        source_videoid=media.FindExtensions('videoid')[0].text,
        source_listid=playlist,
        title=youtube_data.title.text,
        duration=int(media.duration.seconds) if media.duration else 0,
    )
    video.source_category = get_category(media.category)
    for thumbnail in media.thumbnail:
        if 'time' not in thumbnail.extension_attributes:
            video.thumbnails.append(
                VideoThumbnail(
                    url=thumbnail.url,
                    width=thumbnail.width,
                    height=thumbnail.height))
    for restriction in media.FindExtensions('restriction'):
        if restriction.attributes['type'] == 'country':
            video.restrictions.extend(
                VideoRestriction(
                    relationship=restriction.attributes['relationship'],
                    country=country) for country in restriction.text.split())
    return video


def parse_atom_playlist_data(xml):
    """Parse atom feed for youtube video data."""
    feed = gdata.youtube.YouTubePlaylistVideoFeedFromString(xml)
    type, id = feed.id.text.split(':', 3)[2:]
    if type == 'user':
        id = id.replace(':', '/')
    videos = [_get_atom_video_data(e, id) for e in feed.entry]
    return Playlist(feed.title.text, len(videos), videos, None)


def _get_video_data(youtube_data, playlist=None):
    """Extract data from youtube video json record and return Video model."""
    def get_category(categories):
        for category in categories:
            if category['scheme'].endswith('categories.cat'):
                return category['$t']   # TODO: map category
    media = youtube_data['media$group']
    video = Video(
        source_videoid=media['yt$videoid']['$t'],
        source_listid=playlist,
        title=youtube_data['title']['$t'],
        duration=int(media['yt$duration']['seconds']) if 'yt$duration' in media else -1,
    )
    video.source_category = get_category(media.get('media$category', []))
    video.source_view_count = int(youtube_data['yt$statistics']['viewCount']) if 'yt$statistics' in youtube_data else -1
    video.source_date_uploaded = media['yt$uploaded']['$t']
    video.restricted = False
    if 'app$control' in youtube_data:
        if ('yt$incomplete' in youtube_data['app$control'] or
                youtube_data['app$control']['yt$state']['name'] == 'restricted'):
            video.restricted = True
    for thumbnail in media.get('media$thumbnail', []):
        if 'time' not in thumbnail:
            video.thumbnails.append(
                VideoThumbnail(
                    url=thumbnail['url'],
                    width=thumbnail['width'],
                    height=thumbnail['height']))
    for restriction in media.get('media$restriction', []):
        if restriction['type'] == 'country':
            video.restrictions.extend(
                VideoRestriction(
                    relationship=restriction['relationship'],
                    country=country) for country in restriction['$t'].split())
    return video


def _get_video_data_v3(youtube_data, playlist=None):
    snippet = youtube_data['snippet']
    video = Video(
        source_videoid=youtube_data['id']['videoId'],
        source_listid=playlist,
        title=snippet['title'],
        # http://code.google.com/p/gdata-issues/issues/detail?id=4294
        #duration=snippet['duration'],
    )
    video.source_category = None
    video.source_view_count = None
    video.source_date_uploaded = snippet['publishedAt']
    video.restricted = None
    for label, thumbnail in snippet['thumbnails'].items():
        video.thumbnails.append(
            VideoThumbnail(
                url=thumbnail['url'],
                width=None,
                height=None))
    return video


def get_video_data(id, fetch_all_videos=True):
    """Return video data from youtube api as playlist of one."""
    youtube_data = _youtube_feed('videos', id)['entry']
    return Playlist(None, 1, [_get_video_data(youtube_data)], None)


def get_playlist_data(id, fetch_all_videos=False, feed='playlists'):
    """Return playlist data from youtube api."""
    total = 0
    seen = []
    videos = []
    params = {'start-index': 1, 'max-results': (50 if fetch_all_videos else 1)}
    while True:
        youtube_data = _youtube_feed(feed, id, params)['feed']
        total = youtube_data['openSearch$totalResults']['$t']
        limit = min(total, app.config.get('YOUTUBE_IMPORT_LIMIT', 100))
        entries = youtube_data.get('entry', [])
        for entry in entries:
            video = _get_video_data(entry, id)
            if video.source_videoid not in seen and not video.restricted:
                videos.append(video)
                seen.append(video.source_videoid)
        if entries and fetch_all_videos and len(videos) < limit:
            params['start-index'] += params['max-results']
            continue
        break
    links = dict((l['rel'], l['href']) for l in youtube_data['link'])
    if 'hub' in links:
        # strip extraneous query params from topic url
        topic_url = links['self'].split('?', 1)[0] + '?v=2'
        push_config = PushConfig(links['hub'], topic_url)
    else:
        push_config = None
    return Playlist(youtube_data['title']['$t'], total, videos, push_config)


def get_user_data(id, fetch_all_videos=False):
    """Return data for users upload playlist."""
    return get_playlist_data('%s/uploads' % id, fetch_all_videos, 'users')


def search_v2(query, order=None, start=0, size=10, region=None, client_address=None, safe_search='strict'):
    params = {
        'q': query,
        'orderby': order,
        'start-index': start + 1,
        'max-results': size,
        'region': region,
        'restriction': client_address,
        'safeSearch': safe_search,
    }
    data = _youtube_feed('videos', '', params)['feed']
    total = data['openSearch$totalResults']['$t']
    videos = [_get_video_data(e, id) for e in data.get('entry', [])]
    return Videolist(total, [v for v in videos if not v.restricted])


def search_v3(query, order=None, start=0, size=10, region=None, client_address=None, safe_search='strict'):
    # new http instance required for thread-safety
    if not hasattr(_youtube_search_http, 'value'):
        _youtube_search_http.value = httplib2.Http()
    data = _youtube_search.list(
        q=query,
        type='video',
        part='snippet',
        order='date' if order == 'published' else order,
        pageToken=None,     # start number doesn't map to page token easily :-(
        maxResults=size,
        regionCode=region,
        userIp=client_address,
        safeSearch=safe_search,
        videoEmbeddable='true',
    ).execute(http=_youtube_search_http.value)
    total = data['pageInfo']['totalResults']
    videos = [_get_video_data_v3(i) for i in data.get('items', [])]
    return Videolist(total, videos)


if 'search' in app.config.get('USE_YOUTUBE_V3_API', ''):
    from apiclient.discovery import build
    import httplib2
    from threading import local
    _youtube_search = build('youtube', 'v3', developerKey=app.config['GOOGLE_DEVELOPER_KEY']).search()
    _youtube_search_http = local()
    search = search_v3
else:
    search = search_v2


def complete(query, **params):
    url = 'http://www.google.com/complete/search'
    params = dict(client='youtube', ds='yt', q=query, **params)
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.content
