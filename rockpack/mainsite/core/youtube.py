from collections import namedtuple
import requests
from rockpack.mainsite.services.video.models import Video, VideoThumbnail, VideoRestriction


Playlist = namedtuple('Playlist', 'title video_count videos')


def _youtube_feed(feed, id, params={}):
    """Get youtube feed data as json"""
    url = 'http://gdata.youtube.com/feeds/api/%s/%s' % (feed, id)
    params = dict(v=2, alt='json', **params)
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


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
        duration=media['yt$duration']['seconds'] if 'yt$duration' in media else 0,
    )
    video.source_category = category=get_category(media.get('media$category', []))
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
    return Playlist(None, 1, [_get_video_data(youtube_data)])


def get_playlist_data(id, fetch_all_videos=False, feed='playlists'):
    """Return playlist data from youtube api."""
    total = 0
    videos = []
    params = {'start-index': 1, 'max-results': (50 if fetch_all_videos else 1)}
    while True:
        youtube_data = _youtube_feed(feed, id, params)['feed']
        total = youtube_data['openSearch$totalResults']['$t']
        entries = youtube_data.get('entry', [])
        videos.extend(_get_video_data(e, id) for e in entries)
        if entries and fetch_all_videos and len(videos) < total:
            params['start-index'] += params['max-results']
            continue
        break
    return Playlist(youtube_data['title']['$t'], total, videos)


def get_user_data(id, fetch_all_videos=False):
    """Return data for users upload playlist."""
    return get_playlist_data('%s/uploads' % id, fetch_all_videos, 'users')