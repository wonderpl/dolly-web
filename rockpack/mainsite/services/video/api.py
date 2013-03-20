from sqlalchemy.orm import contains_eager
from sqlalchemy.sql.expression import desc
from flask import g, request
from rockpack.mainsite.core.dbapi import db
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
            category=meta.category,
        )
        item.update(channel_dict(meta.channel_rel))
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
    videos = db.session.query(models.VideoInstance, models.Video,
                             models.VideoLocaleMeta).join(models.Video)

    if filters.get('channel'):
        filters.setdefault('channels', [filters['channel']])

    if filters.get('channels'):
        # If selecting videos from a specific channel then we want all videos
        # except those explicitly visible=False for the requested locale.
        # Videos without a locale metadata record will be included.
        videos = videos.outerjoin(models.VideoLocaleMeta,
                    (models.Video.id == models.VideoLocaleMeta.video) &
                    (models.VideoLocaleMeta.locale == loc)).\
            filter((models.VideoLocaleMeta.visible == True) |
                   (models.VideoLocaleMeta.visible == None)).\
            filter(models.VideoInstance.channel.in_(filters['channels']))
    else:
        # For all other queries there must be an metadata record with visible=True
        videos = videos.join(models.VideoLocaleMeta,
                (models.Video.id == models.VideoLocaleMeta.video) &
                (models.VideoLocaleMeta.locale == loc) &
                (models.VideoLocaleMeta.visible == True))

    if filters.get('category'):
        videos = _filter_by_category(videos, models.VideoLocaleMeta, filters['category'][0])

    if filters.get('star_order'):
        videos = videos.order_by(desc(models.VideoLocaleMeta.star_count))

    if filters.get('date_order'):
        videos = videos.order_by(desc(models.VideoInstance.date_added))

    total = videos.count()
    offset, limit = paging
    videos = videos.offset(offset).limit(limit)
    data = []
    for position, v in enumerate(videos, offset):
        item = dict(
            position=position,
            date_added=v.VideoInstance.date_added.isoformat(),
            video=video_dict(v.Video),
            id=v.VideoInstance.id,
            title=v.Video.title,
        )
        if with_channel:
            item['channel'] = channel_dict(v.VideoInstance.video_channel)
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
