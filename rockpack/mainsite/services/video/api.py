import pyes
from sqlalchemy.orm import contains_eager
from sqlalchemy.sql.expression import desc
from flask import request
from rockpack.mainsite import app
from rockpack.mainsite.core.dbapi import db
from rockpack.mainsite.core.es import get_es_connection
from rockpack.mainsite.core.webservice import WebService, expose_ajax
from rockpack.mainsite.services.video import models


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
        metas = _filter_by_category(metas, models.ChannelLocaleMeta, filters['category'])
    if filters.get('query'):
        metas = metas.filter(models.Channel.title.ilike('%%%s%%' % filters['query']))

    if filters.get('date_order'):
        metas = metas.order_by(desc(models.ChannelLocaleMeta.date_added))

    total = metas.count()
    offset, limit = paging
    metas = metas.offset(offset).limit(limit)
    channel_data = []
    for position, meta in enumerate(metas, 1):
        item = dict(
            position=position,
            id=meta.id,
            category=str(meta.category),
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


def es_video_to_channel_map(videos, channel_dict):
    # need to sort these by position
    for video in videos:
        channel_dict[
            video['channel']
        ].setdefault('video', {}
            ).setdefault('items', []).append(video)


def es_owner_to_channel_map(channels, owner_list):
    for channel in channels:
        channel['owner'] = owner_list[channel['owner']]


def es_get_videos(conn, category=None, paging=None, channel_ids=None, star_order=False, locale=None, date_order=False):
    q = pyes.MatchAllQuery()
    terms = []
    if category:
        terms.append(pyes.TermQuery(field='category', value=category))
    if locale:
        terms.append(pyes.TermQuery(field='locale', value=locale))
    if channel_ids:
        q = pyes.FieldQuery()
        q.add('channel', ' '.join(channel_ids))

    sort = ''
    def _append_sort_string(sort_str, field, order='desc'):
        new = field + ':' + order
        if not sort_str:
            return new
        return ','.join(sort_str.split(',').append(new))

    if star_order:
        sort = _append_sort_string(sort, 'star_count')
    if date_order:
        sort = _append_sort_string(sort, 'date_added')

    offset, limit = paging if paging else 0, 100
    # TODO: add ordering

    if terms:
        q = terms[0] if len(terms) == 0 else pyes.BoolQuery(must=terms)

    videos = conn.search(query=pyes.Search(q, start=offset, size=limit), indices='videos', doc_types=['video'], sort=sort)
    return [_ for _ in videos], videos.total


def es_get_owners(conn, ids):
    q = pyes.TermsQuery(field='_id', value=ids)
    return conn.search(query=pyes.Search(q), indices='users', doc_types=['user'])


def es_add_videos(conn, videos):
    for v in videos:
        conn.index({
            'id': v['id'],
            'channel': v['channel']['id'],
            'category': v['category'],
            'title': v['title'],
            'video': {
                'id': v['video']['id'],
                'thumbnail_url': v['video']['thumbnail_url'],
                'view_count': v['video']['view_count']}},
            'en-us',
            'videos',
            id=v['id'])


def es_get_channels(conn, channel_ids=None, category=None, paging=None, locale=None):
    q = pyes.MatchAllQuery()
    # TODO: maybe write this so they can be chained up
    if channel_ids:
        q = pyes.IdsQuery(channel_ids)
    if category:
        q = pyes.TermQuery(field='category', value=category)
    offset, limit = paging if paging else 0, 100
    channels = conn.search(query=pyes.Search(q, start=offset, size=limit), indices='channels', doc_types=['channel'])

    channel_list = {}
    owner_list = {}
    for channel in channels:
        channel_list[channel['id']] = channel
        owner_list[channel['owner']] = None

    for owner in es_get_owners(conn, owner_list.keys()):
        owner_list[owner['id']] = owner
    es_owner_to_channel_map(channel_list.values(), owner_list)
    return channel_list.values(), channels.total


def es_get_channels_with_videos(conn, channel_ids=None, paging=None):
    channels, total = es_get_channels(conn, channel_ids=channel_ids, paging=paging)
    videos, _ = es_get_videos(conn, channel_ids=channel_ids)
    channel_dict = {c['id']: c for c in channels}
    es_video_to_channel_map(videos, channel_dict)
    return channel_dict.values(), total


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
            locale=self.get_locale())

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
