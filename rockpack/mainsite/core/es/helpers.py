from pyes import *

video_mapping = {
        "properties": {
            "id": {"type": "string"},
            "date_added": {"type": "date"},
            "title": {
                "type": "string",
                "index": "analyzed"
                },
            "position": {"type": "integer"},
            "locale": {
                "type": "string",
                "index": "not_analyzed",
                #"_source" : {"enabled" : False}
                },
            "category": {
                "type": "integer"},
            "channel": {
                "type": "string",
                "index": "not_analyzed"
                },
            "video": {
                "properties": {
                    "id": {
                        "type": "string",
                        "index": "not_analyzed"},
                    "thumbnail_url": {
                        "type": "string",
                        "index": "not_analyzed"},
                    "view_count": {"type": "integer"},
                    "star_count": {"type": "integer"},
                    "source": {
                        "type": "string",
                        "index": "not_analyzed"},
                    "source_id": {"type": "string"},
                    "duration": {"type": "integer"}
                    }
                }
            }
        }


owner_mapping = {
        "properties": {
            "avatar_thumbnail_url": {
                "type": "string",
                "index": "not_analyzed"},
            "resource_url": {
                "type": "string",
                "index": "not_analyzed"},
            "display_name": {"type": "string"},
            "name": {"type": "string"},
            "id": {
                "type": "string",
                "index": "not_analyzed"
                }
            }
        }


channel_mapping = {
        "properties": {
            "id": {
                "type": "string",
                "index": "not_analyzed"},
            "locale": {
                "type": "string",
                "index": "not_analyzed"},
            "category": {
                "type": "integer",
                },
            "subscribe_count": {"type": "integer"},
            "description": {
                "type": "string",
                "index": "analyzed"
                },
            "title": {
                "type": "string",
                "index": "analyzed"
                },
            "thumbnail_url": {
                "type": "string",
                "index": "not_analyzed"},
            "cover_thumbnail_small_url": {
                "type": "string",
                "index": "not_analyzed"},
            "cover_thumbnail_large_url": {
                "type": "string",
                "index": "not_analyzed"},
            "cover_background_url": {
                "type": "string",
                "index": "not_analyzed"},
            "resource_url": {
                "type": "string",
                "index": "not_analyzed"},
            "owner": {
                "type": "string",
                        "index": "not_analyzed"}
            }
        }


from rockpack.mainsite import app, init_app
from rockpack.mainsite.core.es import get_es_connection

init_app()

conn = get_es_connection()

try:
    conn.indices.create_index('users')
except:
    pass


try:
    conn.indices.create_index('channels')
except:
    pass


try:
    conn.indices.create_index('videos')
except:
    pass


conn.indices.put_mapping("video", video_mapping, ["videos"])
conn.indices.put_mapping("channel", channel_mapping, ["channels"])

def import_owners():
    from rockpack.mainsite.services.user import models
    with app.test_request_context():
        for user in models.User.query.all():
            print conn.index({
                'id': user.id,
                'avatar_thumbnail': str(user.avatar),
                'resource_url': user.get_resource_url(False),
                'display_name': user.display_name,
                'name': user.username
                },
                'users',
                'user',
                id=user.id)
    print 'done'

def import_channels():
    from rockpack.mainsite.services.video.api import *
    from rockpack.mainsite.services.video.models import Category
    cat_map = {c[0]:c[1] for c in Category.query.filter(Category.parent!=None).values('id', 'parent')}
    with app.test_request_context():
        channels, total = get_local_channel('en-us', (0, 1000,))
        # should keep looping until `total` < whatever
        # the paging amount is
        for c in channels:
            # maybe bulk insert this?
            print conn.index({
                'id': c['id'],
                'subscribe_count': c['subscribe_count'],
                'category': [
                    c['category'],
                    cat_map[c['category']]
                ],
                'locale': 'en-us',
                'description': c['description'],
                'thumbnail_url': c['thumbnail_url'],
                'cover_thumbnail_small_url': c['cover_thumbnail_small_url'],
                'cover_thumbnail_large_url': c['cover_thumbnail_large_url'],
                'cover_background_url': c['cover_background_url'],
                'resource_url': c['resource_url'],
                'title': c['title'],
                'owner': c['owner']['id'],
                },
                'channels',
                'channel',
                id=c['id'])
        print '{} channels'.format(total)
        conn.indices.refresh("channels")

def import_videos():
    from rockpack.mainsite.services.video.api import *
    with app.test_request_context():
        videos, total = get_local_videos('en-us', (0,1000,))
        for v in videos:
            print v['title']
            print conn.index({
                'id': v['id'],
                'channel': v['channel']['id'],
                'locale': 'en-us',
                'category': v['category'],
                'title': v['title'],
                'date_added': v['date_added'],
                'position': v['position'],
                'video': {
                    'id': v['video']['id'],
                    'thumbnail_url': v['video']['thumbnail_url'],
                    'view_count': v['video']['view_count'],
                    'star_count': v['video']['star_count'],
                    'source': v['video']['source'],
                    'source_id': v['video']['source_id'],
                    'duration': v['video']['duration'],
                    }
                },
                'videos',
                'video',
                id=v['id'])


from pprint import pprint as pp
import pyes


def test_q():
    q = pyes.StringQuery('career')
    s = pyes.Search(q)
    r = conn.search(s)
    print [_ for _ in r]


def cat_filter():
    q = pyes.TermQuery(field='category', value=123)
    r = conn.search(query=pyes.Search(q), indices='en-us', doc_types=['channels'])
    pp([_ for _ in r])
