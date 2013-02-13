from flask import request
from rockpack.mainsite.core import youtube
from rockpack.mainsite.core.webservice import WebService, expose
from rockpack.mainsite.core.dbapi import commit_on_success
from rockpack.mainsite.services.video.models import Video
from .models import Subscription


def subscribe(hub, topic, channel_id):
    subs = Subscription(hub=hub, topic=topic, channel_id=channel_id)
    return subs.subscribe()


@commit_on_success
def add_videos_to_channel(channel, videos):
    source = 1  # XXX: Get this dynamically?
    meta = channel.metas[0]
    Video.add_videos(videos, source, meta.locale, meta.category)
    channel.add_videos(videos)


class PubSubHubbub(WebService):

    endpoint = '/pubsubhubbub'

    @expose('/callback', methods=('GET', 'POST'))
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
        elif request.mimetype == 'application/atom+xml':
            sig = request.headers.get('X-Hub-Signature')
            if sig and subs.check_signature(sig, request.data):
                print 'SIG PASSED', sig
            else:
                print 'SIG FAILED', sig
            playlist = youtube.parse_atom_playlist_data(request.data)
            add_videos_to_channel(subs.channel, playlist.videos)
            return '', 204
        else:
            return '', 400
