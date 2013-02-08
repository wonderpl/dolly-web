import random

from sqlalchemy.orm import contains_eager
from sqlalchemy.sql.expression import desc
from flask import g, jsonify, request, url_for
from rockpack.mainsite.core.webservice import WebService
from rockpack.mainsite.core.webservice import expose
from rockpack.mainsite.services.video import models
from rockpack.mainsite.helpers.http import cache_for


def channel_dict(channel):
    sizes = ['thumbnail_large', 'thumbnail_small', 'background']
    images = {'cover_%s_url' % s: getattr(channel.cover, s) for s in sizes}
    url = url_for('UserAPI_api.channel_item',
                  userid=channel.owner_rel.id,
                  channelid=channel.id,
                  _external=True)
    ch_data = dict(
        id=channel.id,
        resource_url=url,
        title=channel.title,
        thumbnail_url=channel.cover.thumbnail_large,
        description=channel.description,
        subscribe_count=random.randint(1, 200),  # TODO: implement this for real
        owner=dict(
            id=channel.owner_rel.id,
            name=channel.owner_rel.username,
            avatar_thumbnail_url=channel.owner_rel.avatar.thumbnail_small,
        )
    )
    ch_data.update(images)
    return ch_data


def get_local_channel(locale, paging, **filters):
    metas = g.session.query(models.ChannelLocaleMeta).\
        filter_by(visible=True, locale=locale)
    if filters.get('category'):
        metas = metas.filter_by(category=filters['category'])
    if filters.get('query'):
        # The contains_eager clause is necessary when filtering on
        # a lazy loaded join.
        metas = metas.join(models.Channel).\
            options(contains_eager(models.ChannelLocaleMeta.channel_rel))
        metas = metas.filter(models.Channel.title.ilike('%%%s%%' % filters['query']))

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


class ChannelAPI(WebService):

    endpoint = '/channels'

    @expose('/', methods=('GET',))
    @cache_for(seconds=300)
    def channel_list(self):
        data, total = get_local_channel(self.get_locale(),
                                        self.get_page(),
                                        category=request.args.get('category'))
        response = jsonify({
            'channels': {
            'items': data,
            'total': total},
        })
        return response


def video_dict(instance):
    # TODO: unfudge this
    thumbnail_url = None
    for t in instance.thumbnails:
        if not thumbnail_url:
            thumbnail_url = t.url
        if t.url.count('mqdefault.jpg'):
            thumbnail_url = t.url
            break

    return dict(
        id=instance.id,
        source=instance.source,
        source_id=instance.source_videoid,
        view_count=instance.view_count,
        star_count=instance.star_count,
        thumbnail_url=thumbnail_url,
    )


def get_local_videos(locale, paging, with_channel=True, **filters):
    videos = g.session.query(models.VideoInstance, models.Video,
                             models.VideoLocaleMeta).join(models.Video)

    if filters.get('channel'):
        # If selecting videos from a specific channel then we want all videos
        # except those explicitly visible=False for the requested locale.
        # Videos without a locale metadata record will be included.
        videos = videos.outerjoin(models.VideoLocaleMeta,
                    (models.Video.id == models.VideoLocaleMeta.video) &
                    (models.VideoLocaleMeta.locale == locale)).\
            filter((models.VideoLocaleMeta.visible == True) |
                   (models.VideoLocaleMeta.visible == None)).\
            filter(models.VideoInstance.channel == filters['channel'])
    else:
        # For all other queries there must be an metadata record with visible=True
        videos = videos.join(models.VideoLocaleMeta,
                (models.Video.id == models.VideoLocaleMeta.video) &
                (models.VideoLocaleMeta.locale == locale) &
                (models.VideoLocaleMeta.visible == True))

    if filters.get('category'):
        videos = videos.filter(models.VideoLocaleMeta.category == filters['category'][0])

    if filters.get('star_order'):
        videos = videos.order_by(desc(models.VideoLocaleMeta.star_count))

    if filters.get('date_order'):
        # XXX: See note below about temporary hack for time distribution
        #videos = videos.order_by(desc(models.VideoInstance.date_added))
        videos = videos.order_by(desc(models.VideoInstance.id))

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
    # XXX: Temporary hack to give nice time distribution for demo
    if 'date_order' in filters:
        from datetime import datetime, timedelta
        now = datetime.now()
        for item in data:
            item['date_added'] = (now - timedelta(14 * random.random())).isoformat()
        data.sort(key=lambda i: i['date_added'], reverse=True)
    return data, total


class VideoAPI(WebService):

    endpoint = '/videos'

    @expose('/', methods=('GET',))
    @cache_for(seconds=300)
    def video_list(self):
        data, total = get_local_videos(self.get_locale(), self.get_page(), star_order=True, **request.args)
        response = jsonify({'videos': {'items': data, 'total': total}})
        response.headers['Cache-Control'] = 'max-age={}'.format(300)  # 5 Mins
        return response


class CategoryAPI(WebService):

    endpoint = '/categories'

    @staticmethod
    def cat_dict(instance):
        d = {'id': instance.id,
             'name': instance.name}
        for c in instance.children:
            d.setdefault('sub_categories', []).append(CategoryAPI.cat_dict(c))

        print d
        return d

    def _get_cats(self, **filters):
        cats = g.session.query(models.Category).filter(
                models.Category.locale == self.get_locale(),
                models.Category.parent == None)

        return [self.cat_dict(c) for c in cats]

    @expose('/', methods=('GET',))
    def category_list(self):
        data = self._get_cats(**request.args)
        response = jsonify({'categories': {'items': data}})
        response.headers['Cache-Control'] = 'max-age={}'.format(300)  # 5 Mins
        return response
