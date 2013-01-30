import random

from flask import (g, jsonify, url_for, abort, request)

from rockpack.mainsite.core.webservice import WebService
from rockpack.mainsite.core.webservice import expose
from rockpack.mainsite.services.video.models import VideoInstance
from rockpack.mainsite.services.video.models import Channel
from rockpack.mainsite.services.video import models


class ChannelAPI(WebService):
    endpoint = '/channels'
    @expose('/', methods=('GET',))
    def channel_list(self):
        data, total = get_local_channel(category=request.args.get('category'))
        response = jsonify({'channels': {
            'items': data,
            'total': total},
            })
        response.headers['Cache-Control'] = 'max-age={}'.format(300)  # 5 Mins
        return response

    @expose('/<string:channel_id>/', methods=('GET',))
    def channel_item(self, channel_id):
        data = get_local_channel(channel_id)
        if not data:
            abort(404)
        response = jsonify({'channel': data})
        response.headers['Cache-Control'] = 'max-age={}'.format(300)  # 5 Mins
        return response


def channel_dict(meta):
    sizes = ['thumbnail_large', 'thumbnail_small', 'background']
    images = {s: getattr(meta.channel_rel.cover, s) for s in sizes}
    return {'id': meta.id,
        'title': meta.channel_rel.title,
        'thumbnail_url': meta.channel_rel.cover.thumbnail_large,
        'images': images,
        'subscribe_count': random.randint(1, 200),  #TODO: implement this for real
        'owner': {'id': meta.channel_rel.owner_rel.id,
            'name': meta.channel_rel.owner_rel.username},
        'category': meta.category,
        }


def get_local_channel(channel_id=None, **filters):
    metas = g.session.query(models.ChannelLocaleMeta)
    if filters.get('category'):
        metas = metas.filter_by(category=filters['category'])
    if channel_id:
        metas = metas.get(channel_id)
        if not metas:
            return None
        return channel_dict(metas)

    metas = metas.filter_by(locale='en-gb')
    count = metas.count()
    channel_data = []
    for meta in metas:
        channel_data.append(channel_dict(meta))

    return channel_data, count


def get_video_dict(instance, route_func_name=None):
    data = {'title': instance.video_video.title,
            'source_id': instance.video_video.source_videoid,
            'date_added': str(instance.date_added),
            'thumbnail_url': instance.video_video.thumbnail_url,
            'star_count': instance.video_video.star_count,
            'channel': get_channel_dict(instance.video_channel),
            }
    if isinstance(route_func_name, str):
        data.update({'resource_uri': PROTOCOL + url_for(route_func_name) + instance.id})
    return data


def channel_item(channel_id):
    channel = g.session.query(Channel).get(channel_id)
    return jsonify(get_channel_dict(channel))


def video_instances():
    video_instances = g.session.query(VideoInstance).all()
    video_list = []
    item_count = 0
    for v in video_instances:
        item_count += 1
        video_list.append(get_video_dict(v, route_func_name='.video_instances'))

    return jsonify({'total': item_count,
        'items': video_list})

def video_instance(item_id):
    video_instance = g.session.query(VideoInstance).get(item_id)
    return jsonify(get_video_dict(video_instance))



