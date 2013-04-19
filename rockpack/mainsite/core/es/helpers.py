from pyes import *

from . import mappings
from . import api

from rockpack.mainsite import app, init_app
from rockpack.mainsite.core.es import get_es_connection

init_app()

conn = get_es_connection()


def delete_index(conn, index):
    conn.indices.delete_index_if_exists(index)


def build_indexes(rebuild=False):
    for index in (mappings.USER_INDEX, mappings.CHANNEL_INDEX, mappings.VIDEO_INDEX):
        if rebuild:
            delete_index(conn, index)
        conn.indices.create_index(index)


conn.indices.put_mapping(mappings.VIDEO_TYPE, mappings.video_mapping, [mappings.VIDEO_INDEX])
conn.indices.put_mapping(mappings.CHANNEL_TYPE, mappings.channel_mapping, [mappings.CHANNEL_INDEX])


def import_owners():
    from rockpack.mainsite.services.user import models
    with app.test_request_context():
        print '--------------- importing owners'
        query = models.User.query.all()
        total = query.count()
        for user in models.User.query.all():
            conn.index({
                'id': user.id,
                'avatar_thumbnail': str(user.avatar),
                'resource_url': user.get_resource_url(False),
                'display_name': user.display_name,
                'name': user.username
                },
                mappings.USER_INDEX,
                mappings.USER_TYPE,
                id=user.id)
    print '{} imported.'.format(total)


def import_channels():
    from rockpack.mainsite.core import es
    from rockpack.mainsite.services.video.models import Category, Channel, _locale_dict_from_object
    conn = es.get_es_connection()

    cat_map = {c[0]:c[1] for c in Category.query.filter(Category.parent!=None).values('id', 'parent')}

    with app.test_request_context():
        print '--------------- importing channels'
        for i, channel in enumerate(Channel.query.filter(Channel.public == True)):
            try:
                category = [channel.category, cat_map[channel.category]] if channel.category else []
            except KeyError:
                category = [channel.category]
            data ={
                'id': channel.id,
                'locale': _locale_dict_from_object(channel.metas),
                'subscribe_count': channel.subscribe_count,
                'category': category,
                'description': channel.description,
                'thumbnail_url': channel.cover.thumbnail_large,
                'cover_thumbnail_small_url': channel.cover.thumbnail_small,
                'cover_thumbnail_large_url': channel.cover.thumbnail_large,
                'cover_background_url': channel.cover.background,
                'resource_url': channel.get_resource_url(),
                'date_added': channel.date_added,
                'title': channel.title,
                'owner_id': channel.owner,
                'ecommerce_url': channel.ecommerce_url
            }
            print api.add_channel_to_index(conn, data)


def import_videos():
    from rockpack.mainsite.core import es
    from rockpack.mainsite.services.video.models import Category, Channel, Video, VideoInstance, _locale_dict_from_object
    conn = es.get_es_connection()
    cat_map = {c[0]:c[1] for c in Category.query.filter(Category.parent!=None).values('id', 'parent')}
    with app.test_request_context():
        query = VideoInstance.query.join(Channel, Video).filter(Video.visible == True, Channel.public == True)
        total = query.count()
        step = 400
        print '--------------- importing videos: stepping in {}s of {}'.format(step, total)
        for i in xrange(0, total, step):
            for v in query.offset(i).limit(step):
                api.add_video_to_index(
                    conn,
                    {'id': v.id,
                    'channel': v.channel,
                    'locale': _locale_dict_from_object(v.metas),
                    'category': [v.category, cat_map[v.category]] if v.category else [],
                    'title': v.video_rel.title,
                    'date_added': v.date_added,
                    'position': v.position,
                    'video_id': v.video,
                    'thumbnail_url': v.video_rel.thumbnails[0].url if v.video_rel.thumbnails else '',
                    'view_count': v.video_rel.view_count,
                    'star_count': v.video_rel.star_count,
                    'source': v.video_rel.source,
                    'source_id': v.video_rel.source_videoid,
                    'duration': v.video_rel.duration,
                    })


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
