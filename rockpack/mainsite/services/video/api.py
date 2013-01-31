import random

from sqlalchemy.sql.expression import desc
from flask import g, jsonify, abort, request, url_for
from rockpack.mainsite.core.webservice import WebService
from rockpack.mainsite.core.webservice import expose
from rockpack.mainsite.services.video import models


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
        metas = g.session.query(models.ChannelLocaleMeta)
        if filters.get('category'):
            metas = metas.filter_by(category=filters['category'])

        metas = metas.filter_by(locale=self.get_locale())
        count = metas.count()
        channel_data = []
        for position, meta in enumerate(metas, 1):
            item = dict(
                position=position,
                id=meta.id,
                category=meta.category,
            )
            item.update(self.channel_dict(meta.channel_rel))
            channel_data.append(item)

        return channel_data, count

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

        return {'source_id': instance.source_videoid,
                'source': instance.source,
                'thumbnail_url': thumbnail_url,
                'id': instance.id}

    def _get_local_videos(self, with_channel=True, **filters):
        vlm = g.session.query(models.VideoInstance, models.VideoLocaleMeta)
        vlm = vlm.filter(models.VideoInstance.video == models.VideoLocaleMeta.video)
        vlm = vlm.filter(models.VideoLocaleMeta.locale == self.get_locale())

        if filters.get('channel'):
            vlm = vlm.filter(models.VideoInstance.channel == filters['channel'])

        if filters.get('category'):
            vlm = vlm.filter(models.VideoLocaleMeta.category == filters['category'][0])

        if filters.get('date_order'):
            vlm = vlm.order_by(desc(models.VideoInstance.date_added))

        if filters.get('star_order'):
            vlm = vlm.order_by(desc(models.VideoLocaleMeta.star_count))

        vlm = vlm.limit(100)  # TODO: artificial limit. needs paging support
        data = []
        total = vlm.count()
        position = 0
        for v in vlm:
            position += 1
            video = self.video_dict(v.VideoInstance.video_rel)
            video['star_count'] = v.VideoLocaleMeta.star_count
            video['view_count'] = v.VideoLocaleMeta.view_count

            item = dict(
                position=position,
                date_added=v.VideoInstance.date_added.isoformat(),
                video=video,
                id=v.VideoInstance.id,
                title=v.VideoInstance.video_rel.title,
            )
            if with_channel:
                item['channel'] = ChannelAPI.channel_dict(v.VideoInstance.video_channel)
            data.append(item)
        return data, total

    @expose('/', methods=('GET',))
    def video_list(self):
        data, total = self._get_local_videos(star_order=True, **request.args)
        response = jsonify({'videos': {'items': data, 'total': total}})
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
