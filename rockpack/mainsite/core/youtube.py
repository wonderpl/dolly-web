from collections import namedtuple
import requests


Video = namedtuple('Video', 'title duration category thumbnails restrictions')
Playlist = namedtuple('Playlist', 'title video_count videos')
Thumbnail = namedtuple('Thumbnail', 'url width height')
Restriction = namedtuple('Restriction', 'relationship country')


def _youtube_feed(feed, id, params={}):
    """Get youtube feed data as json"""
    url = 'http://gdata.youtube.com/feeds/api/%s/%s' % (feed, id)
    params = dict(v=2, alt='json', **params)
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def _get_video_data(youtube_data):
    """Extract relevant data from youtube video json record."""
    def get_category(categories):
        for category in categories:
            if category['scheme'].endswith('categories.cat'):
                return category['$t']   # TODO: map category
    media = youtube_data['media$group']
    video = Video(
        youtube_data['title']['$t'],
        media['yt$duration']['seconds'],
        get_category(media.get('media$category', [])),
        [],
        [],
    )
    for thumbnail in media.get('media$thumbnail', []):
        if 'time' not in thumbnail:
            video.thumbnails.append(
                Thumbnail(thumbnail['url'], thumbnail['width'], thumbnail['height']))
    for restriction in media.get('media$restriction', []):
        if restriction['type'] == 'country':
            video.restrictions.append(
                Restriction(restriction['relationship'], restriction['$t']))
    return video


def get_video_data(id):
    """Return video data from youtube api."""
    youtube_data = _youtube_feed('videos', id)['entry']
    return _get_video_data(youtube_data)


def get_playlist_data(id, fetch_all_videos=False, feed='playlists'):
    """Return playlist data from youtube api."""
    total = 0
    videos = []
    params = {'start-index': 1, 'max-results': (50 if fetch_all_videos else 1)}
    while True:
        youtube_data = _youtube_feed(feed, id, params)['feed']
        total = youtube_data['openSearch$totalResults']['$t']
        videos.extend(_get_video_data(e) for e in youtube_data['entry'])
        if fetch_all_videos and len(videos) < total:
            params['start-index'] += params['max-results']
            continue
        break
    return Playlist(youtube_data['title']['$t'], total, videos)


def get_user_data(id, fetch_all_videos=False):
    """Return data for users upload playlist."""
    return get_playlist_data('%s/uploads' % id, fetch_all_videos, 'users')
