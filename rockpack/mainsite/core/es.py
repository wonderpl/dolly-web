from pyes import *
conn = ES('127.0.0.1:9200')

from pyes.mappings import *
docmapping = DocumentObjectField()

video_mapping = {
        "properties": {
            "id": {"type": "string"},
            "date_added": {"type": "date"},
            "title": {
                "type": "string",
                "index": "analyzed",
                },
            "position": {"type": "integer"},
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
            "resource_url": {"type": "string"}
            }
        }


from rockpack.mainsite.services.video.api import *
from rockpack.mainsite.services.video.models import *
from rockpack.mainsite import app, init_app

init_app()
try:
    conn.indices.create_index('en-us')
except:
    pass


cat_map = {c[0]:c[1] for c in Category.query.filter(Category.parent!=None).values('id', 'parent')}

def import_channels():
    print conn.indices.put_mapping("channels", channel_mapping, ["en-us"])
    with app.test_request_context():
        channels, total = get_local_channel('en-us', (0, 100,))
        # should keep looping until `total` < whatever
        # the paging amount is
        for c in channels:
            # maybe bulk insert this?
            try:
                print conn.index({
                    'locale': 'en-us', 'id': c['id'],
                    'category': [
                        c['category'],
                        cat_map[c['category']]
                    ],
                    'description': c['description'],
                    'description': c['description'],
                    'title': c['title']
                    },
                    'en-us',
                    'channels',
                    id=c['id'])
            except:
                print c
        conn.indices.refresh("en-us")

def import_videos():
    print conn.indices.put_mapping("videos", video_mapping, ["en-us"])
    with app.test_request_context():
        videos, total = get_local_videos('en-us', (0,100,))
        for v in videos:
            print v['title']
            print conn.index({
                'id': v['id'],
                'channel': v['channel']['id'],
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
