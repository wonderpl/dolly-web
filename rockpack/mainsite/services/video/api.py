import urlparse
from flask import request
from collections import defaultdict
from sqlalchemy.orm import contains_eager, lazyload, joinedload
from sqlalchemy.sql.expression import desc
from rockpack.mainsite import app
from rockpack.mainsite.helpers.urls import url_for
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
        subscriber_count=channel.subscriber_count,
        subscribe_count=channel.subscriber_count,   # XXX: backwards compatibility
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
    channels = models.Channel.query.filter_by(public=True, deleted=False).\
        outerjoin(
            models.ChannelLocaleMeta,
            ((models.ChannelLocaleMeta.channel == models.Channel.id) &
            (models.ChannelLocaleMeta.visible == True) &
            (models.ChannelLocaleMeta.locale == locale))).\
        options(lazyload('category_rel'))

    if filters.get('channels'):
        channels = channels.filter(models.Channel.id.in_(filters['channels']))
    if filters.get('category'):
        channels = _filter_by_category(channels, models.Channel, filters['category'])
    if filters.get('query'):
        channels = channels.filter(models.Channel.title.ilike('%%%s%%' % filters['query']))

    if filters.get('date_order'):
        channels = channels.order_by(desc(models.Channel.date_added))

    total = channels.count()
    offset, limit = paging
    channels = channels.offset(offset).limit(limit)
    channel_data = []
    for position, channel in enumerate(channels, offset):
        item = channel_dict(channel)
        item['position'] = position
        channel_data.append(item)

    return channel_data, total


def video_dict(video):
    return dict(
        id=video.id,
        source=['rockpack', 'youtube'][video.source],    # TODO: read source map from db
        source_id=video.source_videoid,
        duration=video.duration,
        view_count=video.view_count,
        star_count=video.star_count,
        thumbnail_url=video.default_thumbnail,
    )


def get_local_videos(loc, paging, with_channel=True, **filters):
    videos = models.VideoInstance.query.join(
        models.Video,
        (models.Video.id == models.VideoInstance.video) &
        (models.Video.visible == True)).\
        options(contains_eager(models.VideoInstance.video_rel))
    if with_channel:
        videos = videos.options(joinedload(models.VideoInstance.video_channel))

    if filters.get('channel'):
        filters.setdefault('channels', [filters['channel']])

    if filters.get('channels'):
        videos = videos.filter(models.VideoInstance.channel.in_(filters['channels']))

    if filters.get('category'):
        videos = _filter_by_category(videos, models.VideoInstance, filters['category'][0])

    if filters.get('position_order'):
        videos = videos.order_by(models.VideoInstance.position)

    if filters.get('star_order'):
        videos = videos.outerjoin(
            models.VideoInstanceLocaleMeta,
            (models.VideoInstanceLocaleMeta.video_instance == models.VideoInstance.id) &
            (models.VideoInstanceLocaleMeta.locale == loc))
        videos = videos.order_by(desc(models.VideoInstanceLocaleMeta.star_count))

    if filters.get('date_order'):
        videos = videos.order_by(desc(models.VideoInstance.date_added))

    total = videos.count()
    offset, limit = paging
    videos = videos.offset(offset).limit(limit)
    data = []
    for position, v in enumerate(videos, offset):
        item = dict(
            position=position,
            date_added=v.date_added.isoformat(),
            video=video_dict(v.video_rel),
            id=v.id,
            title=v.video_rel.title,
        )
        if with_channel:
            item['channel'] = channel_dict(v.video_channel)
        data.append(item)
    return data, total


def es_channel_to_video_map(videos, channel_dict):
    for pos, video in enumerate(videos):
        try:
            video['channel'] = channel_dict[video['channel']]
        except KeyError:
            pass


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


def es_get_videos(category=None, paging=None, channel_ids=None, star_order=None, locale=None, date_order='desc', position=None):
    search = IndexSearch('video', locale)
    if category:
        search.add_term('category', category)
    if channel_ids:
        search.add_term('channel', channel_ids)

    search_kwargs = {}
    sorting = _sort_string(star_order=star_order, position=position, date_added=date_order)
    if sorting:
        search_kwargs.update(sorting)
    if paging:
        search_kwargs.update(
            {'start': paging[0],
            'limit': paging[1]})

    videos = search.search(**search_kwargs)

    vlist = []
    for pos, v in enumerate(videos):
        # XXX: should return either datetime or isoformat - something is broken
        v['date_added'] = v['date_added'].isoformat() if not isinstance(v['date_added'], unicode) else v['date_added']
        if v['category']:
            v['category'] = max(v['category']) if isinstance(v['category'], list) else v['category']
        else:
            # v['category'] could be a list. We need pass an empty string if no data
            v['category'] = ''
        if locale:
            v['video']['view_count'] = v['locale'][locale]['view_count']
            v['video']['star_count'] = v['locale'][locale]['star_count']
        del v['locale']
        v['position'] = pos
        vlist.append(v)
    return vlist, videos.total


def es_get_owners(ids):
    search = IndexSearch('user', None)
    search.add_term('_id', ids)
    return search.search()


def es_get_channels(channel_ids=None, category=None, paging=None, locale=None, star_order=None, date_order=None):
    search = IndexSearch('channel', locale)
    if channel_ids:
        search.add_ids(channel_ids)
    if category:
        search.add_term('category', category)

    sorting = _sort_string(star_order=star_order, date_added=date_order)

    offset, limit = paging if paging else 0, 100
    channels = search.search(offset, limit, sort=sorting.get('sort', ''))

    channel_list = []
    owner_list = {}
    for pos, channel in enumerate(channels):
        del channel['locale']
        channel['position'] = pos
        try:
            del channel['date_added']
        except KeyError:
            pass

        # XXX: tis a bit dangerous to assume max(cat)
        # is the child category. review this
        for k, v in channel.iteritems():
            if isinstance(v, (str, unicode)) and k.endswith('_url'):
                url = v
                if k == 'resource_url':
                    url = urlparse.urljoin(url_for('basews.discover'), v)
                elif k != 'ecommerce_url':
                    url = urlparse.urljoin(app.config.get('IMAGE_CDN', ''), v)
                channel[k] = url
            if k == 'category':
                channel[k] = max(channel[k]) if channel[k] and isinstance(channel[k], list) else channel[k]

        channel_list.append(channel)
        owner_list[channel['owner']] = None

    for owner in es_get_owners(owner_list.keys()):
        owner['resource_url'] = urlparse.urljoin(url_for('basews.discover'), owner['resource_url'])
        owner['avatar_thumbnail'] = urlparse.urljoin(app.config.get('IMAGE_CDN', ''), owner['avatar_thumbnail'])
        owner_list[owner['id']] = owner
    es_owner_to_channel_map(channel_list, owner_list)
    return channel_list, channels.total


def es_get_channels_with_videos(channel_ids=None, paging=None):
    channels, total = es_get_channels(channel_ids=channel_ids, paging=paging)
    for c in channels:
        videos, vtotal = es_get_videos(channel_ids=channel_ids, position='asc')
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

        videos, total = es_get_videos(
            category=category,
            paging=self.get_page(),
            star_order=request.args.get('star_order'),
            locale=self.get_locale(),
            date_order=request.args.get('date_order'))

        channels, _ = es_get_channels(channel_ids=[v['channel'] for v in videos])

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

        channels, total = es_get_channels(
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

    @expose_ajax('/', cache_age=3600)
    def category_list(self):
        translations = dict((c.category, (c.name, c.priority)) for c in
                            models.CategoryTranslation.query.filter_by(locale=self.get_locale()))
        items = []
        children = defaultdict(list)
        for cat in models.Category.query.all():
            name, priority = translations.get(cat.id, (None, None))
            if name:
                info = dict(id=str(cat.id), name=name, priority=priority)
                if cat.parent:
                    children[cat.parent].append(info)
                else:
                    info['sub_categories'] = children[cat.id]
                    items.append(info)
        return dict(categories=dict(items=items))
