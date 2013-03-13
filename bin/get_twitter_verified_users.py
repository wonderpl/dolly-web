#!/usr/bin/python2.7
import time
import twitter
import logging
from rockpack.mainsite import app, init_app
from rockpack.mainsite.services.user.models import ReservedUsername


VERIFIED_USER_ID = 63796828
SLEEP_TIME = 12     # limit is 350 requests/hour


api = twitter.Api(
    consumer_key=app.config['TWITTER_CONSUMER_KEY'],
    consumer_secret=app.config['TWITTER_CONSUMER_SECRET'],
    access_token_key=app.config['TWITTER_ACCESS_TOKEN_KEY'],
    access_token_secret=app.config['TWITTER_ACCESS_TOKEN_SECRET'])


def retry(f, count=3, **kwargs):
    while True:
        try:
            time.sleep(SLEEP_TIME)
            logging.info('calling %s %r', f.__name__, kwargs)
            return f(**kwargs)
        except Exception, e:
            if not count:
                logging.exception('failed %s %r', f.__name__, kwargs)
                return
            logging.warning('retrying %s %r (%s)', f.__name__, kwargs, e)
            count -= 1


def get_twitter_verified_users():
    cursor = -1
    while True:
        friends = retry(api.GetFriendIDs, user=VERIFIED_USER_ID, cursor=cursor)
        for uid in map(str, friends['ids']):
            if not ReservedUsername.query.filter_by(
                    external_system='twitter', external_uid=uid).count():
                user = retry(api.GetUser, user=uid)
                if user:
                    yield user.screen_name, uid, str(user)
        cursor = friends.get('next_cursor')
        if not cursor:
            break


if __name__ == '__main__':
    init_app()
    logging.basicConfig(level=logging.INFO)

    for username, uid, data in get_twitter_verified_users():
        ReservedUsername(
            username=username,
            external_system='twitter',
            external_uid=uid,
            external_data=data,
        ).save()
