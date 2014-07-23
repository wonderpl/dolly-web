from datetime import datetime
from sqlalchemy.exc import IntegrityError
from flask import request, json
from rockpack.mainsite import app
from rockpack.mainsite.core import youtube
from rockpack.mainsite.core.webservice import WebService, expose, secure_view
from rockpack.mainsite.core.dbapi import commit_on_success
from rockpack.mainsite.services.video.models import Video, VideoThumbnail, Source
from .models import Subscription


def subscribe(hub, topic, channel_id):
    if Subscription.query.filter_by(topic=topic).count():
        raise Exception('Subscription to topic already exists: %s' % topic)
    subs = Subscription(hub=hub, topic=topic, channel_id=channel_id)
    subs.subscribe()
    return subs


@commit_on_success
def _update_channel_videos(channel, data):
    playlist = youtube.parse_atom_playlist_data(data)
    source = Source.label_to_id('youtube')
    Video.add_videos(playlist.videos, source)
    channel.add_videos(playlist.videos)


def update_channel_videos(channel, data):
    # pubsubhubbub.appspot.com often duplicates the same update request
    # and since it can take a while to parse a big feed request we can
    # get duplicate key errors when the concurrent transactions are committed.
    for retry in 1, 0:
        try:
            _update_channel_videos(channel, data)
        except IntegrityError:
            if retry:
                continue
            else:
                raise
        else:
            break


@commit_on_success
def update_romeo_videos(data):
    vdata = data['video']
    assert vdata['source'] == 'ooyala'
    source = Source.label_to_id(vdata['source'])

    # update existing or create new
    key = dict(source=source, source_videoid=vdata['source_id'])
    video = Video.query.filter_by(**key).first() or Video(**key).add()

    video.title = data['title']
    video.description = vdata['description']
    video.duration = vdata['duration']
    video.date_published = datetime.strptime(
        vdata['source_date_uploaded'][:19], '%Y-%m-%dT%H:%M:%S')
    video.source_username = vdata['source_username']
    video.link_url = vdata['link_url']
    video.link_title = vdata['link_title']
    video.category = data['category']
    video.thumbnails = [VideoThumbnail(**t) for t in data['thumbnails']]


class PubSubHubbubWS(WebService):

    endpoint = '/pubsubhubbub'

    @expose('/callback', methods=('GET', 'POST'))
    @secure_view()
    def callback(self):
        try:
            id = int(request.args.get('id', ''))
        except ValueError:
            return '', 400
        subs = Subscription.query.get_or_404(id)
        if request.args.get('hub.mode') in ('subscribe', 'unsubscribe'):
            args = [request.args.get('hub.' + a, '') for a in
                    'topic', 'verify_token', 'lease_seconds', 'challenge']
            response = subs.verify(*args)
            return (response, 200) if response else ('', 404)
        elif request.mimetype in ('application/atom+xml', 'application/json'):
            sig = request.headers.get('X-Hub-Signature')
            if sig and subs.check_signature(sig, request.data):
                if 'romeo.wonderpl.com' in subs.topic:
                    update_romeo_videos(json.loads(request.data))
                else:
                    # assume youtube
                    update_channel_videos(subs.channel, request.data)
            else:
                app.logger.warning('Failed to validate signature %s', sig)
            return '', 204
        else:
            return '', 400
