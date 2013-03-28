import re
import logging
from datetime import datetime
from rockpack.mainsite.manager import manager
from .models import Subscription

@manager.command
def refresh_pubsubhubbub_subscriptions(id=None):
    """Re-subscribe expired PubSubHubbub subscriptions."""
    if id:
        subs = [Subscription.query.get(id)]
    else:
        subs = Subscription.query.filter(Subscription.lease_expires < datetime.now())

    for sub in subs:
        try:
            sub.subscribe()
        except Exception, e:
            if hasattr(e, 'response'):
                message = re.sub('.*<h2>([^<]+).*', '\\1', e.response.text, 1, re.DOTALL)
                logging.error('Failed to subscribe: %d: %d: %s', sub.id, e.response.status_code, message)
            else:
                logging.exception('Failed to subscribe: %d', sub.id)
        else:
            logging.info('Subscribed: %d', sub.id)
