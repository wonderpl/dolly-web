import random

from flask import g, jsonify, abort, request
from rockpack.mainsite.core.webservice import WebService
from rockpack.mainsite.core.webservice import expose
from rockpack.mainsite.services.video import models


class ChannelAPI(WebService):

    endpoint = '/channels'

    @staticmethod
    def channel_dict(channel):
        sizes = ['thumbnail_large', 'thumbnail_small', 'background']
        images = {'cover_%s_url' % s: getattr(channel.cover, s) for s in sizes}
        ch_data = {
            'title': channel.title,
            'thumbnail_url': channel.cover.thumbnail_large,
            'subscribe_count': random.randint(1, 200),  # TODO: implement this for real
            'owner': {
                'id': channel.owner_rel.id,
                'name': channel.owner_rel.username,
                'avatar_thumbnail_url': channel.owner_rel.avatar.thumbnail_small,
            }
        }
        ch_data.update(images)
        return ch_data

    def _get_local_channel(self, channel_id=None, **filters):
        metas = g.session.query(models.ChannelLocaleMeta)
        if filters.get('category'):
            metas = metas.filter_by(category=filters['category'])
        if channel_id:
            metas = metas.get(channel_id)
            if not metas:
                return None
            return self.channel_dict(metas.channel_rel)

        metas = metas.filter_by(locale=self.get_locale())
        count = metas.count()
        channel_data = []
        for meta in metas:
            ch = {'category': meta.category, 'id': meta.id}
            ch.update(self.channel_dict(meta.channel_rel))
            channel_data.append(ch)

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

    @expose('/<string:channel_id>/', methods=('GET',))
    def channel_item(self, channel_id):
        data = self._get_local_channel(channel_id)
        if not data:
            abort(404)
        response = jsonify({'channel': data})
        response.headers['Cache-Control'] = 'max-age={}'.format(300)  # 5 Mins
        return response


class VideoAPI(WebService):

    endpoint = '/videos'

    def _get_local_videos(self, **filters):
        vlm = g.session.query(models.VideoInstance)
        vlm = vlm.join(models.VideoLocaleMeta, models.VideoInstance.video == models.VideoLocaleMeta.video)
        vlm = vlm.filter(models.VideoLocaleMeta.locale == self.get_locale())

        if filters.get('category'):
            vlm = vlm.filter(models.VideoLocaleMeta.category == filters['category'][0])

        vlm = vlm.limit(100)  # TODO: artificial limit. needs paging support
        data = []
        total = vlm.count()
        for v in vlm:
            data.append({
                'date_added': v.date_added.isoformat(),
                'video': self.video_dict(v.video_rel),
                'id': v.id,
                'channel': ChannelAPI.channel_dict(v.video_channel),
                'title': v.video_rel.title})
        return data, total

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
                'id': instance.id,
                'star_count': instance.star_count}

    @expose('/', methods=('GET',))
    def video_list(self):
        data, total = self._get_local_videos(**request.args)
        response = jsonify({'videos': {'items': data, 'total': total}})
        response.headers['Cache-Control'] = 'max-age={}'.format(300)  # 5 Mins
        return response
