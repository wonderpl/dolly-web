import functools
from collections import namedtuple

from flask import Blueprint
from flask import jsonify
from flask import json
from flask import url_for

from rockpack.core.dbapi import session
from rockpack.services.video.models import VideoInstance
from rockpack.services.video.models import Channel

video = Blueprint('video_api', __name__)

# TODO: do this someother way. hack for now
PROTOCOL = 'http://localhost:5000' # leading slash already exists for root url

service_urls = namedtuple('ServiceUrl', 'url func_name func methods')
def expose(url, methods=['GET']):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # attach the url details to the wrapper so we can use it later

        if not hasattr(wrapper, '_service_urls'):
            wrapper._service_urls = []
        wrapper._service_urls.append(service_urls(url=url, func_name=func.__name__, func=func, methods=methods))

        return wrapper

    return decorator

class APIMeta(type):
    def __new__(cls, name, bases, dict_):
        try:
            WebService
        except NameError:
            return type.__new__(cls, name, bases, dict_)

        routes = {}
        # we need to get any service urls from expose()
        for value in dict_.values():
            if callable(value):
                urls = getattr(value, '_service_urls', ())
                for url in urls:
                    routes.setdefault(url.url, url)

        dict_['_routes'] = routes.values()
        return type.__new__(cls, name, bases, dict_)

import types

class WebService(object):
    __metaclass__ = APIMeta

    def __init__(self, app, url_prefix, **kwargs):

        bp = Blueprint(self.__class__.__name__ + '_api', self.__class__.__name__)
        for route in self._routes:
            bp.add_url_rule(route.url,
                    route.func.__name__,
                    view_func=types.MethodType(route.func, self, self.__class__),
                    methods=route.methods)

        app.register_blueprint(bp)


class ChannelAPI(WebService):
    @expose('/test_channel/', methods=('GET',))
    def test_channel(self):
        channels = session.query(Channel).all()
        return jsonify({'items': [get_channel_dict(c) for c in channels]})



def get_channel_dict(instance, route_func_name=None):
    data = {'id': instance.id,
            'title': instance.title,
            'thumbnail_url': instance.thumbnail_url
            }
    if isinstance(route_func_name, str):
        data.update({'resource_ur': PROTOCOL + url_for(route_func_name) + instance.id})
    return data

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

@video.route('/channels/')
def channel_list():
    channels = session.query(Channel).all()
    return jsonify({'items': [get_channel_dict(c, route_func_name='.channel_list') for c in channels]})

@video.route('/channels/<channel_id>')
def channel_item(channel_id):
    channel = session.query(Channel).get(channel_id)
    return jsonify(get_channel_dict(channel))

@video.route('/videos/')
def video_instances():
    video_instances = session.query(VideoInstance).all()
    video_list = []
    item_count = 0
    for v in video_instances:
        item_count += 1
        video_list.append(get_video_dict(v, route_func_name='.video_instances'))

    return jsonify({'total': item_count,
        'items': video_list})

@video.route('/videos/<item_id>')
def video_instance(item_id):
    video_instance = session.query(VideoInstance).get(item_id)
    return jsonify(get_video_dict(video_instance))



