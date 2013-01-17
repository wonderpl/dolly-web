from flask import Blueprint
from flask import jsonify
from flask import url_for

from rockpack.mainsite.core.webservice import WebService
from rockpack.mainsite.core.webservice import expose
from rockpack.mainsite.core.dbapi import session
from rockpack.mainsite.services.video.models import VideoInstance
from rockpack.mainsite.services.video.models import Channel

video = Blueprint('video_api', __name__)

# TODO: do this someother way. hack for now
PROTOCOL = 'http://localhost:5000' # leading slash already exists for root url

class ChannelAPI(WebService):
    endpoint = '/test'
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



