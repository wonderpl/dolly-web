import pyes
from sqlalchemy.orm import contains_eager
from sqlalchemy.sql.expression import desc
from flask import request
from rockpack.mainsite import app
from rockpack.mainsite.core.dbapi import db
from rockpack.mainsite.core.es import get_es_connection
from rockpack.mainsite.core.webservice import WebService, expose_ajax
from rockpack.mainsite.services.video import models
from rockpack.mainsite.core.es.api import IndexSearch


def _filter_by_category(query, type, category_id):
    """Filter given query by the specified category.
    If top-level category given, then filter by all sub categories.
    """
    sub_cats = list(models.Category.query.filter_by(parent=category_id).
                    values(models.Category.id))
    cat_ids = zip(*sub_cats)[0] if sub_cats else [category_id]
    return query.filter(type.category.in_(cat_ids))


def channel_dict(channel, with_owner=True, owner_url=False):
    sizes = ['thumbnail_large', 'thumbnail_small', 'background']
    images = {'cover_%s_url' % s: getattr(channel.cover, s) for s in sizes}
    ch_data = dict(
        id=channel.id,
        resource_url=channel.get_resource_url(owner_url),
        title=channel.title,
        thumbnail_url=channel.cover.thumbnail_large,
        description=channel.description,
        subscribe_count=0,  # TODO: implement this for real
        public=channel.public,
        category=channel.category,
    )
    if with_owner:
        ch_data['owner'] = dict(
            id=channel.owner_rel.id,
            resource_url=channel.owner_rel.get_resource_url(owner_url),
            display_name=channel.owner_rel.display_name,
            name=channel.owner_rel.display_name,    # XXX: backwards compatibility
            avatar_thumbnail_url=channel.owner_rel.avatar.thumbnail_small,
        )
    ch_data.update(images)
    return ch_data


def get_local_channel(locale, paging, **filters):
    metas = models.ChannelLocaleMeta.query.filter_by(visible=True, locale=locale)
    metas = metas.join(models.Channel).\
        options(contains_eager(models.ChannelLocaleMeta.channel_rel))
    metas = metas.filter(models.Channel.public==True, models.Channel.deleted==False)
    if filters.get('category'):
        metas = _filter_by_category(metas, models.Channel, filters['category'])
    if filters.get('query'):
        metas = metas.filter(models.Channel.title.ilike('%%%s%%' % filters['query']))

    if filters.get('date_order'):
        metas = metas.order_by(desc(models.ChannelLocaleMeta.date_added))

    total = metas.count()
    offset, limit = paging
    metas = metas.offset(offset).limit(limit)
    channel_data = []
    for position, meta in enumerate(metas, offset):
        item = dict(
            position=position,
            id=meta.id,
        )
        item.update(channel_dict(meta.channel_rel))
        channel_data.append(item)

    return channel_data, total


def video_dict(video):
    # TODO: unfudge this
    thumbnail_url = None
    for t in video.thumbnails:
        if not thumbnail_url:
            thumbnail_url = t.url
        if t.url.count('mqdefault.jpg'):
            thumbnail_url = t.url
            break

    return dict(
        id=video.id,
        source=['rockpack', 'youtube'][video.source],    # TODO: read source map from db
        source_id=video.source_videoid,
        duration=video.duration,
        view_count=video.view_count,
        star_count=video.star_count,
        thumbnail_url=thumbnail_url,
    )


def get_local_videos(loc, paging, with_channel=True, **filters):
    videos = db.session.query(models.VideoInstance, models.Video
            ).join(models.Video
            ).filter(models.Video.visible == True
                    ).outerjoin(models.VideoInstanceLocaleMeta,
                            (models.VideoInstanceLocaleMeta.video_instance == models.VideoInstance.id) &
                            (models.VideoInstanceLocaleMeta.locale == loc))

    if filters.get('channel'):
        filters.setdefault('channels', [filters['channel']])

    if filters.get('channels'):
        videos = videos.filter(models.VideoInstance.channel.in_(filters['channels']))

    if filters.get('category'):
        videos = _filter_by_category(videos, models.VideoInstance, filters['category'][0])

    if filters.get('position_order'):
        videos = videos.order_by(models.VideoInstance.position)

    if filters.get('star_order'):
        videos = videos.order_by(desc(models.VideoInstanceLocaleMeta.star_count))

    if filters.get('date_order'):
        videos = videos.order_by(desc(models.VideoInstance.date_added))

    total = videos.count()
    offset, limit = paging
    videos = videos.offset(offset).limit(limit)
    data = []
    for position, v in enumerate(videos, offset):
        cats = []
        if v.VideoInstance.category:
            cats.append(v.VideoInstance.category_ref.id)
            if v.VideoInstance.category_ref.parent:
                cats.append(v.VideoInstance.category_ref.parent)

        item = dict(
            category=cats,
            position=v.VideoInstance.position,
            date_added=v.VideoInstance.date_added.isoformat(),
            video=video_dict(v.Video),
            id=v.VideoInstance.id,
            title=v.Video.title,
        )
        if with_channel:
            item['channel'] = channel_dict(v.VideoInstance.video_channel)
        data.append(item)
    return data, total


def es_channel_to_video_map(videos, channel_dict):
    for pos, video in enumerate(videos, len(videos)):
        try:
            video['channel'] = channel_dict[video['channel']]
            video['position'] = pos
        except KeyError:
            pass


def es_video_to_channel_map(videos, channel_dict, total):
    # need to sort these by position
    for video in videos:
        channel_dict[
            video['channel']
        ].setdefault('video', {}
            ).setdefault('items', []).append(video)
    channel_dict['video']['total'] = total


def es_owner_to_channel_map(channels, owner_list):
    for channel in channels:
        channel['owner'] = owner_list[channel['owner']]


def _sort_string(**kwargs):
    sort = []
    for k, v in kwargs.iteritems():
        if v is not None:
            if v.lower() != 'asc':
                v = 'desc'
            sort.append('{}:{}'.format(k.lower(), v.lower()))
    return {'sort': ','.join(sort)} if sort else {}

def es_get_videos(conn, category=None, paging=None, channel_ids=None, star_order=None, locale=None, date_order=None, position=None):
    search = IndexSearch(conn, 'video', locale)
    if category:
        search.add_term('category', category)
    if channel_ids:
        search.add_term('channel', channel_ids)

    search_kwargs = {}
    sorting = _sort_string(star_order=star_order, date_added=date_order, position=position)
    if sorting:
        search_kwargs.update(sorting)
    if paging:
        search_kwargs.update(
            {'start': paging[0],
            'limit': paging[1]})

    videos = search.search(**search_kwargs)

    vlist = []
    for v in videos:
        # XXX: should return either datetime or isoformat - something is broken
        v['date_added'] = v['date_added'].isoformat() if not isinstance(v['date_added'], unicode) else v['date_added']
        v['category'] = max(v['category']) if isinstance(v['category'], list) else v['category']
        if locale:
            v['video']['view_count'] = v['locale'][locale]['view_count']
            v['video']['star_count'] = v['locale'][locale]['star_count']
        del v['locale']
        vlist.append(v)
    return vlist, videos.total


def es_get_owners(conn, ids):
    q = pyes.TermsQuery(field='_id', value=ids)
    return conn.search(query=pyes.Search(q), indices='users', doc_types=['user'])


def es_get_channels(conn, channel_ids=None, category=None, paging=None, locale=None, star_order=None, date_order=None):
    search = IndexSearch(conn, 'channel', locale)
    if channel_ids:
        search.add_ids(channel_ids)
    if category:
        search.add_term('category', category)

    sorting = _sort_string(star_order=star_order, date_added=date_order)

    offset, limit = paging if paging else 0, 100
    channels = search.search(offset, limit, sort=sorting.get('sort', ''))

    channel_list = []
    owner_list = {}
    for channel in channels:
        del channel['locale']
        try:
            del channel['date_added']
        except KeyError:
            pass
        # XXX: tis a bit dangerous to assume max(cat)
        # is the child category. review this
        channel['category'] = max(channel['category']) if isinstance(channel['category'], list) else channel['category']
        channel_list.append(channel)
        owner_list[channel['owner']] = None

    for owner in es_get_owners(conn, owner_list.keys()):
        owner_list[owner['id']] = owner
    es_owner_to_channel_map(channel_list, owner_list)
    return channel_list, channels.total


def es_get_channels_with_videos(conn, channel_ids=None, paging=None):
    channels, total = es_get_channels(conn, channel_ids=channel_ids, paging=paging)
    for c in channels:
        videos, vtotal = es_get_videos(conn, channel_ids=channel_ids, position='asc')
        c.setdefault('videos', {}).setdefault('items', videos)
        c['videos']['total'] = vtotal
    return channels, total


class VideoWS(WebService):

    endpoint = '/videos'

    @expose_ajax('/', cache_age=300)
    def video_list(self):
        if not app.config.get('ELASTICSEARCH_URL'):
            data, total = get_local_videos(self.get_locale(), self.get_page(), star_order=True, **request.args)
            return dict(videos=dict(items=data, total=total))

        category = request.args.get('category')

        conn = get_es_connection()
        videos, total = es_get_videos(conn,
                category=category,
                paging=self.get_page(),
                star_order=request.args.get('star_order'),
                locale=self.get_locale(),
                date_order=request.args.get('date_order'))

        channels, _ = es_get_channels(conn, channel_ids=[v['channel'] for v in videos])

        es_channel_to_video_map(videos, {c['id']: c for c in channels})

        return dict(videos={'items': videos},
                total=total)


class ChannelWS(WebService):

    endpoint = '/channels'

    @expose_ajax('/', cache_age=300)
    def channel_list(self):
        if not app.config.get('ELASTICSEARCH_URL'):
            data, total = get_local_channel(self.get_locale(),
                    self.get_page(),
                    category=request.args.get('category'))
            return dict(channels=dict(items=data, total=total))

        conn = get_es_connection()
        channels, total = es_get_channels(conn,
            category=request.args.get('category'),
            paging=self.get_page(),
            locale=self.get_locale(),
            star_order=request.args.get('star_order'),
            date_order=request.args.get('date_order'))

        return dict(
            channels=dict(
                items=channels,
                total=total))


class CategoryWS(WebService):

    endpoint = '/categories'

    @staticmethod
    def cat_dict(instance):
        data = dict(
            id=str(instance.id),
            name=instance.name,
            priority=instance.priority,
        )
        for c in instance.children:
            data.setdefault('sub_categories', []).append(CategoryWS.cat_dict(c))
        return data

    def _get_cats(self, **filters):
        cats = models.Category.query.filter_by(locale=self.get_locale(), parent=None)
        return [self.cat_dict(c) for c in cats]

    @expose_ajax('/', cache_age=3600)
    def category_list(self):
        data = self._get_cats(**request.args)
        return dict(categories=dict(items=data))
