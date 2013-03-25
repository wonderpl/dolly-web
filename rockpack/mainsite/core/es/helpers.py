from pyes import *

video_mapping = {
        "properties": {
            "id": {"type": "string"},
            "date_added": {"type": "date"},
            "title": {
                "type": "string",
                "index": "analyzed",
                },
            "position": {"type": "integer"},
            "category": {
                "type": "integer",
                "index": "analyzed"},
            "channel": {
                "type": "string",
                "index": "analyzed"},
            "video": {
                "properties": {
                    "id": {"type": "string"},
                    "thumbnail_url": {"type": "string"},
                    "source_id": {"type": "string"},
                    "view_count": {"type": "integer"}
                    }
                }
            }
        }


owner_mapping = {
        "properties": {
            "avatar_thumbnail_url": {"type": "string"},
            "resource_url": {"type": "string"},
            "display_name": {"type": "string"},
            "name": {"type": "string"},
            "id": {
                "type": "string",
                "index": "analyzed"
                }
            }
        }


channel_mapping = {
        "properties": {
            "id": {"type": "string"},
            "locale": {"type": "string"},
            "category": {
                "type": "integer",
                "index": "analyzed"
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
            "thumbnail_url": {"type": "string"},
            "cover_thumbnail_small_url": {"type": "string"},
            "cover_thumbnail_large_url": {"type": "string"},
            "cover_background_url": {"type": "string"},
            "resource_url": {"type": "string"},
            "owner": {"type": "string"}
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


# Should loop through app.config.ENABLED_LOCALES
try:
    conn.indices.create_index('en-us')
except:
    pass

try:
    conn.indices.create_index('en-gb')
except:
    pass

conn.indices.put_mapping("videos", video_mapping, ["en-us"])
conn.indices.put_mapping("channels", channel_mapping, ["en-us"])

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
                'description': c['description'],
                'thumbnail_url': c['thumbnail_url'],
                'cover_thumbnail_small_url': c['cover_thumbnail_small_url'],
                'cover_thumbnail_large_url': c['cover_thumbnail_large_url'],
                'cover_background_url': c['cover_background_url'],
                'resource_url': c['resource_url'],
                'title': c['title'],
                'owner': c['owner']['id'],
                },
                'en-us',
                'channels',
                id=c['id'])
        print '{} channels'.format(total)
        conn.indices.refresh("en-us")

def import_videos():
    from rockpack.mainsite.services.video.api import *
    with app.test_request_context():
        videos, total = get_local_videos('en-us', (0,1000,))
        for v in videos:
            print v['title']
            print conn.index({
                'id': v['id'],
                'channel': v['channel']['id'],
                'category': v['category'],
                'title': v['title'],
                'video': {
                    'id': v['video']['id'],
                    'thumbnail_url': v['video']['thumbnail_url'],
                    'view_count': v['video']['view_count']
                    }
                },
                'en-us',
                'videos',
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
