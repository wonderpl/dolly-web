from datetime import datetime, timedelta
import requests
from flask import request, url_for
from rockpack.mainsite.core.webservice import WebService, expose
from .models import Subscription


LEASE_SECONDS = 60 * 60 * 24


def subscribe(hub, topic):
    lease_expires = datetime.now() + timedelta(seconds=LEASE_SECONDS)
    verify_token = 'xyzzy'
    callback_url = url_for('PubSubHubbub_api.callback', _external=True)
    callback_url = callback_url.replace('localhost', 'dev.rockpack.com')
    subs = Subscription(hub=hub, topic=topic,
                        verify_token=verify_token, lease_expires=lease_expires)
    data = {
        'hub.callback': callback_url,
        'hub.mode': 'subscribe',
        'hub.topic': topic,
        'hub.verify': 'async',
        'hub.lease_seconds': LEASE_SECONDS,
        'hub.verify_token': verify_token,
    }
    response = requests.post(hub, data)
    response.raise_for_status()
    subs.save()


def verify(topic, verify_token, lease_seconds, challenge):
    subs = Subscription.query.filter_by(
        topic=topic, verify_token=verify_token).first_or_404()
    subs.verified = True
    subs.lease_seconds = lease_seconds
    subs.save()
    return challenge


class PubSubHubbub(WebService):

    endpoint = '/pubsubhubbub'

    @expose('/callback', methods=('GET', 'POST'))
    def callback(self):
        if request.args.get('hub.mode') == 'subscribe':
            args = [request.args.get('hub.' + a, '') for a in
                    'topic', 'verify_token', 'lease_seconds', 'challenge']
            return verify(*args), 200
        elif request.method == 'POST':
            print 'HEADERS', repr(request.headers)
            print 'ARGS', repr(request.args)
            print 'FORM', repr(request.form)
            print 'DATA', request.data
            return '', 204
        else:
            return '', 400
