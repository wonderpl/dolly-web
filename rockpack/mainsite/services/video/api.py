from collections import defaultdict
from sqlalchemy.orm import contains_eager, lazyload, joinedload
from sqlalchemy.sql.expression import desc
from flask import request
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


class ChannelWS(WebService):

    endpoint = '/channels'

    @expose_ajax('/', cache_age=300)
    def channel_list(self):
        data, total = get_local_channel(self.get_locale(),
                                        self.get_page(),
                                        category=request.args.get('category'))
        return dict(channels=dict(items=data, total=total))


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


class VideoWS(WebService):

    endpoint = '/videos'

    @expose_ajax('/', cache_age=300)
    def video_list(self):
        data, total = get_local_videos(self.get_locale(), self.get_page(), star_order=True, **request.args)
        return dict(videos=dict(items=data, total=total))


class CategoryWS(WebService):

    endpoint = '/categories'

    @expose_ajax('/', cache_age=3600)
    def category_list(self):
        items = []
        children = defaultdict(list)
        for cat in models.Category.query.filter(models.CategoryTranslation.category == models.Category.id,
                models.CategoryTranslation.locale == self.get_locale()):
            info = dict(id=str(cat.id), name=cat.translations[0].name, priority=cat.translations[0].priority)
            if cat.parent:
                children[cat.parent].append(info)
            else:
                info['sub_categories'] = children[cat.id]
                items.append(info)
        return dict(categories=dict(items=items))
