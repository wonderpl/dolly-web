from collections import namedtuple
import requests
from rockpack.mainsite import app
from rockpack.mainsite.services.video.models import Video, VideoThumbnail, VideoRestriction


PushConfig = namedtuple('PushConfig', 'hub topic')
Playlist = namedtuple('Playlist', 'title video_count videos push_config')
Videolist = namedtuple('Videolist', 'video_count videos')


def _youtube_feed(feed, id, params={}):
    """Get youtube feed data as json"""
    url = 'http://gdata.youtube.com/feeds/api/%s/%s' % (feed, id)
    params = dict(v=2, alt='json', **params)
    response = requests.get(url, params=params)
    response.raise_for_status()
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
    import gdata.youtube
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
        duration=int(media['yt$duration']['seconds']) if 'yt$duration' in media else 0,
    )
    video.source_category = get_category(media.get('media$category', []))
    video.source_view_count = int(youtube_data['yt$statistics']['viewCount'])
    video.source_date_uploaded = media['yt$uploaded']['$t']
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


def get_video_data(id, fetch_all_videos=True):
    """Return video data from youtube api as playlist of one."""
    youtube_data = _youtube_feed('videos', id)['entry']
    return Playlist(None, 1, [_get_video_data(youtube_data)], None)


def get_playlist_data(id, fetch_all_videos=False, feed='playlists'):
    """Return playlist data from youtube api."""
    total = 0
    videos = []
    params = {'start-index': 1, 'max-results': (50 if fetch_all_videos else 1)}
    while True:
        youtube_data = _youtube_feed(feed, id, params)['feed']
        total = youtube_data['openSearch$totalResults']['$t']
        limit = min(total, app.config.get('YOUTUBE_IMPORT_LIMIT', 100))
        entries = youtube_data.get('entry', [])
        videos.extend(_get_video_data(e, id) for e in entries)
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


def search(query, start=0, size=10, region=None, client_address=None, safe_search='strict'):
    params = {
        'q': query,
        'start-index': start + 1,
        'max-results': size,
        'region': region,
        'restriction': client_address,
        'safeSearch': safe_search,
    }
    data = _youtube_feed('videos', '', params)['feed']
    total = data['openSearch$totalResults']['$t']
    videos = [_get_video_data(e, id) for e in data.get('entry', [])]
    return Videolist(total, videos)


def complete(query, **params):
    url = 'http://www.google.com/complete/search'
    params = dict(client='youtube', ds='yt', q=query, **params)
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.content
