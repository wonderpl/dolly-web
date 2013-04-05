from pyes import *

from . import mappings
from . import api

from rockpack.mainsite import app, init_app
from rockpack.mainsite.core.es import get_es_connection

init_app()

conn = get_es_connection()



try:
    conn.indices.create_index(mappings.USER_INDEX)
except:
    pass


try:
    conn.indices.create_index(mappings.CHANNEL_INDEX)
except:
    pass


try:
    conn.indices.create_index(mappings.VIDEO_INDEX)
except:
    pass


conn.indices.put_mapping(mappings.VIDEO_TYPE, mappings.video_mapping, [mappings.VIDEO_INDEX])
conn.indices.put_mapping(mappings.CHANNEL_TYPE, mappings.channel_mapping, [mappings.CHANNEL_INDEX])


def delete_index(conn, index):
    conn.indices.delete_index_if_exists(index)


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
                mappings.USER_INDEX,
                mappings.USER_TYPE,
                id=user.id)
    print 'done'

def import_channels():
    from rockpack.mainsite.services.video.api import *
    from rockpack.mainsite.services.video.models import Category

    cat_map = {c[0]:c[1] for c in Category.query.filter(Category.parent!=None).values('id', 'parent')}

    for locale in ('en-us', 'en-gb', ):
        with app.test_request_context():
            for c in ChannelLocaleMeta.query.all():
                api.add_channel_to_index(conn, channel)
            return conn.indices.refresh(CHANNEL_INDEX)
            
            channels, total = get_local_channel(locale, (0, 1000,))
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
                    mappings.CHANNEL_INDEX,
                    mappings.CHANNEL_TYPE,
                    id=c['id'])
            print '{} channels'.format(total)
            conn.indices.refresh("channels")

def import_videos():
    from rockpack.mainsite.services.video.api import *
    for locale in ('en-us', 'en-gb', ):
        with app.test_request_context():
            videos, total = get_local_videos(locale, (0,1000,))
            for v in videos:
                print v['title']
                print conn.index({
                    'id': v['id'],
                    'channel': v['channel']['id'],
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
                    mappings.VIDEO_INDEX,
                    mappings.VIDEO_TYPE,
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
