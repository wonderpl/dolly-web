from flask import request
from collections import defaultdict
from sqlalchemy.orm import contains_eager, lazyload, joinedload
from sqlalchemy.sql.expression import desc
from rockpack.mainsite import app
from rockpack.mainsite.core.webservice import WebService, expose_ajax
from rockpack.mainsite.services.video import models
from rockpack.mainsite.core.es import use_elasticsearch, filters
from rockpack.mainsite.core.es.api import VideoSearch, ChannelSearch


def _filter_by_category(query, type, category_id):
    """Filter given query by the specified category.
    If top-level category given, then filter by all sub categories.
    """
    sub_cats = list(models.Category.query.filter_by(parent=category_id).
                    values(models.Category.id))
    cat_ids = zip(*sub_cats)[0] if sub_cats else [category_id]
    return query.filter(type.category.in_(cat_ids))


def channel_dict(channel, with_owner=True, owner_url=False):
    ch_data = dict(
        id=channel.id,
        resource_url=channel.get_resource_url(owner_url),
        title=channel.title,
        subscriber_count=channel.subscriber_count,
        category=channel.category,
        cover=dict(
            thumbnail_url=channel.cover.url,
            aoi=channel.cover_aoi,
        )
    )
    if channel.favourite:
        ch_data['favourites'] = True
    if with_owner:
        ch_data['owner'] = dict(
            id=channel.owner_rel.id,
            resource_url=channel.owner_rel.get_resource_url(owner_url),
            display_name=channel.owner_rel.display_name,
            avatar_thumbnail_url=channel.owner_rel.avatar.thumbnail_small,
        )
    if owner_url:
        ch_data['public'] = channel.public
    if app.config.get('SHOW_CHANNEL_DESCRIPTION', False):
        ch_data['description'] = channel.description
    if app.config.get('SHOW_OLD_CHANNEL_COVER_URLS', True):
        for k in 'thumbnail_large', 'thumbnail_small', 'background':
            ch_data['cover_%s_url' % k] = getattr(channel.cover, k)
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


def video_dict(instance):
    video = instance.video_rel
    return dict(
        id=instance.id,
        title=video.title,
        date_added=instance.date_added.isoformat(),
        video=dict(
            id=video.id,
            source=['rockpack', 'youtube'][video.source],    # TODO: read source map from db
            source_id=video.source_videoid,
            source_username=video.source_username,
            duration=video.duration,
            view_count=video.view_count,
            star_count=video.star_count,
            thumbnail_url=video.default_thumbnail,
        )
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
    for position, video in enumerate(videos, offset):
        item = video_dict(video)
        item['position'] = position
        if with_channel:
            item['channel'] = channel_dict(video.video_channel)
        data.append(item)
    return data, total


class VideoWS(WebService):

    endpoint = '/videos'

    @expose_ajax('/', cache_age=300)
    def video_list(self):
        if not use_elasticsearch():
            data, total = get_local_videos(self.get_locale(), self.get_page(), star_order=True, **request.args)
            return dict(videos=dict(items=data, total=total))

        category = request.args.get('category')

        vs = VideoSearch(self.get_locale())
        offset, limit = self.get_page()
        vs.set_paging(offset, limit)
        vs.filter_category(category)
        vs.star_order_sort(request.args.get('star_order'))
        vs.date_sort(request.args.get('date_order'))
        videos = vs.videos(with_channels=True)
        total = vs.total

        return dict(videos={'items': videos}, total=total)

    @expose_ajax('/players/', cache_age=7200)
    def players(self):
        return dict(models.Source.query.values(models.Source.label, models.Source.player_template))


class ChannelWS(WebService):

    endpoint = '/channels'

    @expose_ajax('/', cache_age=300)
    def channel_list(self):
        if not use_elasticsearch():
            data, total = get_local_channel(
                self.get_locale(),
                self.get_page(),
                category=request.args.get('category'))
            return dict(channels=dict(items=data, total=total))

        cs = ChannelSearch(self.get_locale())
        offset, limit = self.get_page()
        cs.set_paging(offset, limit)
        # Boost popular channels based on ...
        cs.add_filter(filters.boost_from_field_value('editorial_boost'))
        cs.add_filter(filters.boost_from_field_value('subscriber_count'))
        cs.add_filter(filters.boost_from_field_value('update_frequency'))
        view_count_field = '.'.join(['locales', self.get_locale(), 'view_count'])
        star_count_field = '.'.join(['locales', self.get_locale(), 'star_count'])
        cs.add_filter(filters.boost_from_field_value(view_count_field))
        cs.add_filter(filters.boost_from_field_value(star_count_field))
        cs.filter_category(request.args.get('category'))
        cs.date_sort(request.args.get('date_order'))
        if request.args.get('user_id'):
            cs.add_term('owner', request.args.get('user_id'))
        channels = cs.channels(with_owners=True)
        total = cs.total

        return dict(
            channels=dict(
                items=channels,
                total=total
            )
        )


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
