import random

from sqlalchemy.sql.expression import desc
from flask import g, jsonify, abort, request, url_for
from rockpack.mainsite.core.webservice import WebService
from rockpack.mainsite.core.webservice import expose
from rockpack.mainsite.services.video import models
from flask.ext.sqlalchemy import get_debug_queries


class ChannelAPI(WebService):

    endpoint = '/channels'

    @staticmethod
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

    def _get_local_channel(self, **filters):
        metas = g.session.query(models.ChannelLocaleMeta).\
            filter_by(visible=True, locale=self.get_locale())
        if filters.get('category'):
            metas = metas.filter_by(category=filters['category'])

        total = metas.count()
        offset, limit = self.get_page()
        metas.offset(offset).limit(limit)
        channel_data = []
        for position, meta in enumerate(metas, offset):
            item = dict(
                position=position,
                id=meta.id,
                category=meta.category,
            )
            item.update(self.channel_dict(meta.channel_rel))
            channel_data.append(item)

        return channel_data, total

    @expose('/', methods=('GET',))
    def channel_list(self):
        data, total = self._get_local_channel(category=request.args.get('category'))
        response = jsonify({
            'channels': {
            'items': data,
            'total': total},
        })
        response.headers['Cache-Control'] = 'max-age={}'.format(300)  # 5 Mins
        return response


class VideoAPI(WebService):

    endpoint = '/videos'

    @staticmethod
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

    def _get_local_videos(self, with_channel=True, **filters):
        videos = g.session.query(models.VideoInstance, models.Video,
                                 models.VideoLocaleMeta).join(models.Video)

        if filters.get('channel'):
            # If selecting videos from a specific channel then we want all videos
            # except those explicitly visible=False for the requested locale.
            # Videos without a locale metadata record will be included.
            videos = videos.outerjoin(models.VideoLocaleMeta,
                        (models.Video.id == models.VideoLocaleMeta.video) &
                        (models.VideoLocaleMeta.locale == self.get_locale())).\
                filter((models.VideoLocaleMeta.visible == True) |
                       (models.VideoLocaleMeta.visible == None)).\
                filter(models.VideoInstance.channel == filters['channel'])
        else:
            # For all other queries there must be an metadata record with visible=True
            videos = videos.join(models.VideoLocaleMeta,
                    (models.Video.id == models.VideoLocaleMeta.video) &
                    (models.VideoLocaleMeta.locale == self.get_locale()) &
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
        offset, limit = self.get_page()
        videos = videos.offset(offset).limit(limit)
        data = []
        for position, v in enumerate(videos, offset):
            item = dict(
                position=position,
                date_added=v.VideoInstance.date_added.isoformat(),
                video=self.video_dict(v.Video),
                id=v.VideoInstance.id,
                title=v.Video.title,
            )
            if with_channel:
                item['channel'] = ChannelAPI.channel_dict(v.VideoInstance.video_channel)
            data.append(item)
        # XXX: Temporary hack to give nice time distribution for demo
        if 'date_order' in filters:
            from datetime import datetime, timedelta
            now = datetime.now()
            for item in data:
                item['date_added'] = (now - timedelta(14 * random.random())).isoformat()
            data.sort(key=lambda i: i['date_added'], reverse=True)
        return data, total

    @expose('/', methods=('GET',))
    def video_list(self):
        data, total = self._get_local_videos(star_order=True, **request.args)
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
                models.Category.locale==self.get_locale(),
                models.Category.parent==None)

        return [self.cat_dict(c) for c in cats]

    @expose('/', methods=('GET',))
    def category_list(self):
        data = self._get_cats(**request.args)
        response = jsonify({'categories': {'items': data}})
        response.headers['Cache-Control'] = 'max-age={}'.format(300)  # 5 Mins
        return response


class UserAPI(VideoAPI):

    endpoint = '/'

    @expose('/<userid>/subscriptions/recent_videos/')
    def recent_videos(self, userid):
        data, total = self._get_local_videos(date_order=True, **request.args)
        response = jsonify({'videos': {'items': data, 'total': total}})
        response.headers['Cache-Control'] = 'max-age={}'.format(300)  # 5 Mins
        return response

    @expose('/<userid>/channels/<string:channelid>/', methods=('GET',))
    def channel_item(self, userid, channelid):
        meta = g.session.query(models.ChannelLocaleMeta).filter_by(
            channel=channelid).first()
        if not meta:
            abort(404)
        data = ChannelAPI.channel_dict(meta.channel_rel)
        items, total = self._get_local_videos(channel=channelid, with_channel=False)
        data['videos'] = dict(items=items, total=total)
        response = jsonify(data)
        response.headers['Cache-Control'] = 'max-age={}'.format(300)  # 5 Mins
        return response
