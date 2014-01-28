import time
import re
import urlparse
from itertools import izip_longest, groupby
from datetime import datetime, timedelta
from flask import json
from sqlalchemy import func, text, between, case, desc, distinct
from sqlalchemy.orm import joinedload, contains_eager, aliased
from sqlalchemy.orm.exc import NoResultFound
from rockpack.mainsite import app
from rockpack.mainsite.manager import manager, job_control
from rockpack.mainsite.core.dbapi import commit_on_success, db, readonly_session
from rockpack.mainsite.core import email
from rockpack.mainsite.core.token import create_unsubscribe_token
from rockpack.mainsite.core.apns import push_client
from rockpack.mainsite.helpers.urls import url_tracking_context
from rockpack.mainsite.services.oauth import facebook
from rockpack.mainsite.services.oauth.models import ExternalFriend, ExternalToken
from rockpack.mainsite.services.video.models import Channel, VideoInstanceComment, VideoInstance, Video
from rockpack.mainsite.services.share.models import ShareLink
from .models import (
    User, UserActivity, UserAccountEvent, UserNotification, UserContentFeed,
    UserFlag, UserInterest, Subscription, BroadcastMessage)


def _notification_user_info(user):
    # NOTE: This will store full image urls in database
    return dict(
        id=user.id,
        resource_url=user.get_resource_url(),
        display_name=user.display_name,
        avatar_thumbnail_url=user.avatar.thumbnail_medium,
    )


def _notification_channel_info(channel, own=True):
    return dict(
        id=channel.id,
        resource_url=channel.get_resource_url(own),
        title=channel.title,
        thumbnail_url=channel.cover.thumbnail_medium,
    )


def _notification_video_info(video_instance, channel):
    return dict(
        id=video_instance.id,
        resource_url=video_instance.resource_url,
        thumbnail_url=video_instance.default_thumbnail,
        channel=dict(
            id=channel.id,
            resource_url=channel.get_resource_url(True),
        )
    )


def subscribe_message(activity, channel):
    return channel.owner, 'subscribed', dict(
        user=_notification_user_info(activity.actor),
        channel=_notification_channel_info(channel),
    )


def star_message(activity, video_instance):
    channel = video_instance.video_channel
    return channel.owner, 'starred', dict(
        user=_notification_user_info(activity.actor),
        video=_notification_video_info(video_instance, channel),
    )


def repack_message(repacker, channel, video_instance):
    return channel.owner, 'repack', dict(
        user=_notification_user_info(repacker),
        video=_notification_video_info(video_instance, channel),
    )


def comment_mention_message(commenter, channel, video_instance):
    return 'comment_mention', dict(
        user=_notification_user_info(commenter),
        video=_notification_video_info(video_instance, channel)
    )


def unavailable_video_message(channel, video_instance):
    return channel.owner, 'unavailable', dict(
        user=_notification_user_info(channel.owner_rel),
        video=_notification_video_info(video_instance, channel),
    )


def joined_message(friend, user):
    return friend, 'joined', dict(
        user=_notification_user_info(user),
    )


def _apns_url(url):
    return urlparse.urlparse(url).path.lstrip('/ws/')


def _send_apns_message(user, token, message):
    try:
        srv = push_client.APNs(push_client.connection)
        result = srv.send(push_client.Message(token, **message))
        if result.errors or result.failed:
            app.logger.error('Failed to send message to %s: %r: %r: %r',
                             user, message, result.errors, result.failed)
        else:
            app.logger.info('Sent message to %s: %r', user, message)
        return result
    except Exception:
        app.logger.exception('Failed to send push notification: %d', message.get('id', 0))


def _process_apns_broadcast(users, alert, url=None):
    # Fake notification id passed because iOS app won't follow url without it :-(
    message = dict(alert=alert, id=0)
    if url:
        message['url'] = _apns_url(url)
    # batch push calls into chunks of 100 (unique) tokens
    for tokens in izip_longest(*[(t for u, t in users)] * 100, fillvalue=None):
        _send_apns_message('batch', filter(None, set(tokens)), message)


def _add_user_notification(user, date_created, message_type, message_body):
    UserNotification(
        user=user,
        date_created=date_created,
        message_type=message_type,
        message=json.dumps(message_body, separators=(',', ':')),
    ).add()


def complex_push_notification(token, push_message, push_message_args, badge=None, id=None, url=None):
    message = dict(
        alert={
            "loc-key": push_message,
            "loc-args": push_message_args
        }
    )
    if badge is not None:
        message.update({'badge': badge})
    if id is not None:
        message.update({'id': id})
    if url is not None:
        message.update({'url': url})
    return _send_apns_message(token.user, token.external_token, message)


def get_apns_token(user_id):
    try:
        return ExternalToken.query.filter(
            ExternalToken.external_system == 'apns',
            ExternalToken.external_token != 'INVALID',
            ExternalToken.user == user_id).one()
    except NoResultFound:
        return


def send_push_notifications(user):
    try:
        user_id = user.id
    except:
        user_id = user
    token = get_apns_token(user_id)
    if not token:
        return

    notifications = UserNotification.query.filter_by(date_read=None, user=user_id).order_by('id desc')
    count = notifications.count()
    app.logger.debug('%s notification count: %d', user_id, count)

    # Send most recent notification only
    notification = sorted(notifications, key=lambda n: n.id, reverse=True)[0]
    data = json.loads(notification.message)

    if notification.message_type == 'subscribed':
        key = 'channel'
        push_message = "%@ has subscribed to your channel"
    elif notification.message_type == 'joined':
        key = 'user'
        push_message = "Your Facebook friend %@ has joined Rockpack"
    elif notification.message_type == 'repack':
        key = 'video'
        push_message = "%@ has re-packed one of your videos"
    elif notification.message_type == 'unavailable':
        key = 'video'
        push_message = "One of your videos is no longer available"
    elif notification.message_type == 'comment_mention':
        key = 'video'
        push_message = "%@ has mentioned you in a comment"
    else:
        key = 'video'
        push_message = "%@ has liked your video"
    try:
        push_message_args = [data['user']['display_name']]
    except KeyError:
        push_message_args = []
    deeplink_url = _apns_url(data[key]['resource_url'])

    return complex_push_notification(
        token, push_message, push_message_args,
        badge=count, id=notification.id, url=deeplink_url)


def create_unavailable_notifications(date_from=None, date_to=None, user_notifications=None):
    activity_window = readonly_session.query(VideoInstance, Video, Channel).join(
        Video,
        Video.id == VideoInstance.video
    ).join(
        Channel,
        Channel.id == VideoInstance.channel
    ).options(
        joinedload(Channel.owner_rel)
    ).filter(
        Video.visible == False
    )
    if date_from:
        activity_window = activity_window.filter(Video.date_updated >= date_from)
    if date_to:
        activity_window = activity_window.filter(Video.date_updated < date_to)

    for video_instance, video, channel in activity_window:
        user, message_type, message = unavailable_video_message(channel, video_instance)
        _add_user_notification(user, video.date_updated, message_type, message)
        if user_notifications is not None:
            user_notifications.setdefault(user, None)


def create_new_repack_notifications(date_from=None, date_to=None, user_notifications=None):
    packer_channel = aliased(Channel, name="source_channel")
    packer_user = aliased(User, name="packer_user")
    repacker_channel = aliased(Channel, name="repacker_channel")
    repacker_user = aliased(User, name="repacker_user")

    activity_window = readonly_session.query(VideoInstance, packer_channel, repacker_channel, repacker_user).join(
        packer_channel,
        packer_channel.id == VideoInstance.source_channel
    ).join(
        packer_user,
        packer_user.id == packer_channel.owner
    ).join(
        repacker_channel,
        (repacker_channel.id == VideoInstance.channel) &
        (repacker_channel.favourite == False) &
        (repacker_channel.public == True)
    ).join(
        repacker_user,
        repacker_user.id == repacker_channel.owner
    )
    if date_from:
        activity_window = activity_window.filter(VideoInstance.date_added >= date_from)
    if date_to:
        activity_window = activity_window.filter(VideoInstance.date_added < date_to)

    for video_instance, packer_channel, repacker_channel, repacker in activity_window:
        user, type, body = repack_message(repacker, repacker_channel, video_instance)

        _add_user_notification(packer_channel.owner, video_instance.date_added, type, body)
        if user_notifications is not None:
            user_notifications.setdefault(packer_channel.owner, None)


def create_new_activity_notifications(date_from=None, date_to=None, user_notifications=None):
    activity_notification_map = dict(
        # map action -> activity list, object model, message function
        subscribe=([], Channel, subscribe_message),
        star=([], VideoInstance, star_message),
    )

    activity_window = UserActivity.query.options(joinedload('actor'))
    if date_from:
        activity_window = activity_window.filter(UserActivity.date_actioned >= date_from)
    if date_to:
        activity_window = activity_window.filter(UserActivity.date_actioned < date_to)
    for activity in activity_window:
        if activity.action in activity_notification_map:
            activity_notification_map[activity.action][0].append(activity)

    for action, (activity_list, model, get_message) in activity_notification_map.items():
        if activity_list:
            object_ids = [a.object_id for a in activity_list]
            objects = dict((o.id, o) for o in model.query.filter(model.id.in_(object_ids)))
            for activity in activity_list:
                object = objects.get(activity.object_id)
                app.logger.info('read activity %d: %s: %s',
                                activity.id, action, getattr(object, 'id', None))
                if object:
                    user, type, body = get_message(activity, object)
                    if user == activity.user:
                        # Don't send notifications to self
                        continue
                    _add_user_notification(user, activity.date_actioned, type, body)
                    if user_notifications is not None:
                        user_notifications.setdefault(user, None)


def create_new_registration_notifications(date_from=None, date_to=None, user_notifications=None):
    new_users = User.query.join(ExternalToken, (
        (ExternalToken.user == User.id) &
        (ExternalToken.external_system == 'facebook'))
    ).options(contains_eager(User.external_tokens))
    if date_from:
        new_users = new_users.filter(User.date_joined >= date_from)
    if date_to:
        new_users = new_users.filter(User.date_joined < date_to)
    for user in new_users:
        token = user.external_tokens[0]
        friends = ExternalFriend.query.\
            filter_by(external_system=token.external_system, external_uid=token.external_uid).\
            values(ExternalFriend.user)
        for friend, in friends:
            friend, message_type, message = joined_message(friend, user)
            _add_user_notification(friend, user.date_joined, message_type, message)
            if user_notifications is not None:
                user_notifications.setdefault(friend, None)


def create_commmenter_notification(date_from=None, date_to=None, user_notifications=None):
    comments = VideoInstanceComment.query.join(
        User, User.id == VideoInstanceComment.user
    ).join(
        VideoInstance, VideoInstance.id == VideoInstanceComment.video_instance
    ).join(
        Channel, Channel.id == VideoInstance.channel
    ).with_entities(
        VideoInstanceComment, User, VideoInstance, Channel
    ).filter(VideoInstanceComment.comment.like('%@%'))

    if date_from:
        comments = comments.filter(VideoInstanceComment.date_added >= date_from)
    if date_to:
        comments = comments.filter(VideoInstanceComment.date_added < date_to)

    # username -> video_instance
    commented_on_users = {}

    COMMENTEE_RE = re.compile('@(\w+)')

    # We're going to check the usernames from the regex in one go
    # instead of one by one, so collate them all here first
    for comment, user, video_instance, channel in comments:
        usernames = COMMENTEE_RE.findall(comment.comment)
        for username in usernames:
            commented_on_users.setdefault(username.lower(), []).append((user, video_instance, channel, comment.date_added,))

    # Now find all the valid users
    if commented_on_users:
        valid_users = User.query.filter(func.lower(User.username).in_(commented_on_users.keys()))

        for user in valid_users:
            for commenter, video_instance, channel, date_added in commented_on_users.get(user.username.lower()):
                type, body = comment_mention_message(commenter, channel, video_instance)
                _add_user_notification(user.id, date_added, type, body)
                if user_notifications is not None:
                    user_notifications.setdefault(user.id, None)


def remove_old_notifications():
    """Remove old messages but leave at least N notifications per user."""
    threshold_days, threshold_count = app.config.get('KEEP_OLD_NOTIFICATIONS', (30, 100))
    target_users = UserNotification.query.\
        with_entities(UserNotification.user).\
        group_by(UserNotification.user).\
        having(func.count(UserNotification.id) > threshold_count)
    count = UserNotification.query.\
        filter(UserNotification.date_created < (datetime.now() - timedelta(threshold_days))).\
        filter(UserNotification.user.in_(target_users)).\
        delete(False)
    app.logger.info('deleted %d notifications', count)


def update_video_feed_item_stars(date_from, date_to):
    # Find all star actions in this interval for which a friend of the star'ing user
    # has the video in their feed and update the stars list with these new stars at
    # the top.
    feed_items = UserContentFeed.query.\
        join(UserActivity,
            (UserActivity.action == 'star') &
            (UserActivity.date_actioned.between(date_from, date_to))).\
        join(ExternalToken, ExternalToken.user == UserActivity.user).\
        join(ExternalFriend, (ExternalFriend.external_system == ExternalToken.external_system) &
                             (ExternalFriend.external_uid == ExternalToken.external_uid)).\
        join(VideoInstance, UserActivity.object_id == VideoInstance.id).\
        filter((UserContentFeed.user == ExternalFriend.user) &
               (UserContentFeed.channel == VideoInstance.channel) &
               (UserContentFeed.video_instance == VideoInstance.id)).\
        with_entities(UserContentFeed, func.string_agg(UserActivity.user, ' ')).\
        group_by(UserContentFeed.id)
    star_limit = app.config.get('FEED_STARS_LIMIT', 3)
    for feed_item, new_stars in feed_items:
        old_stars = json.loads(feed_item.stars) if feed_item.stars else []
        new_stars = [l for l in new_stars.split() if l not in old_stars]
        stars = (new_stars + old_stars)[:star_limit]
        feed_item.stars = json.dumps(stars)


def create_new_video_feed_items(date_from, date_to):
    # Create a new feed record for every user that's subscribed to the channels of new videos
    UserContentFeed.query.session.add_all(
        UserContentFeed(user=user, channel=channel, video_instance=video, date_added=date_added)
        for user, channel, video, date_added in
        VideoInstance.query.filter(
            VideoInstance.date_added.between(date_from, date_to)).
        join(Subscription, Subscription.channel == VideoInstance.channel).
        outerjoin(
            UserContentFeed,
            (UserContentFeed.user == Subscription.user) &
            (UserContentFeed.channel == VideoInstance.channel) &
            (UserContentFeed.video_instance == VideoInstance.id)).
        filter(UserContentFeed.id == None).
        values(Subscription.user, VideoInstance.channel, VideoInstance.id, VideoInstance.date_added)
    )


def create_new_channel_feed_items(date_from, date_to):
    # Create new feed record for every user that's
    # subscribed to a channel owned by
    # or
    # a friend of
    # the publisher of new channels in this interval
    SubChannel = aliased(Channel, name='subchannel')
    new_channels = Channel.query.filter(
        Channel.date_published.between(date_from, date_to))
    sub_channels = new_channels.\
        join(SubChannel, Channel.owner == SubChannel.owner).\
        join(Subscription, Subscription.channel == SubChannel.id)
    friend_channels = new_channels.\
        join(ExternalToken, ExternalToken.user == Channel.owner).\
        join(ExternalFriend, (ExternalFriend.external_system == ExternalToken.external_system) &
                             (ExternalFriend.external_uid == ExternalToken.external_uid))

    channelmeta = dict((c.id, (c.owner_rel.display_name, c.resource_url)) for c in new_channels)
    notification_groups = {}
    notify_users = {}

    for query, U in (sub_channels, Subscription), (friend_channels, ExternalFriend):
        # use outerjoin to filter existing records
        q = query.outerjoin(
            UserContentFeed,
            (UserContentFeed.user == U.user) &
            (UserContentFeed.channel == Channel.id) &
            (UserContentFeed.video_instance == None)
        ).filter(
            UserContentFeed.id == None
        ).distinct().values(U.user, Channel.id, Channel.date_published)

        for user, channel, date_published in q:
            UserContentFeed.query.session.add(
                UserContentFeed(user=user, channel=channel, date_added=date_published)
            )
            notification_groups.setdefault(channel, set()).add(user)
            notify_users.update({user: None})

    [notify_users.update({user: token}) for user, token in
        ExternalToken.query.filter(
            ExternalToken.external_system == 'apns', ExternalToken.user.in_(notify_users.keys())
        ).values(ExternalToken.user, ExternalToken.external_token)]

    for channel, users in notification_groups.iteritems():
        tokens = []
        map(lambda u: tokens.append([u, notify_users.get(u, None)]), users)
        display_name, channel_resource_url = channelmeta[channel]
        alert = {
            "loc-key": '%@ has added a new channel',
            "loc-args": [display_name]
        }
        if tokens:
            _process_apns_broadcast(tokens, alert, url=channel_resource_url)


def remove_old_feed_items():
    """Remove old records but leave at least N records per user."""
    threshold_days, threshold_count = app.config.get('KEEP_OLD_FEED_ITEMS', (30, 1000))
    target_users = UserContentFeed.query.\
        with_entities(UserContentFeed.user).\
        group_by(UserContentFeed.user).\
        having(func.count(UserContentFeed.id) > threshold_count)
    count = UserContentFeed.query.\
        filter(UserContentFeed.date_added < (datetime.now() - timedelta(threshold_days))).\
        filter(UserContentFeed.user.in_(target_users)).\
        delete(False)
    app.logger.info('deleted %d feed items', count)


def _send_email_or_log(user, template, **ctx):
    try:
        body = template.render(
            email_sender=app.config['DEFAULT_EMAIL_SOURCE'],
            assets=app.config.get('ASSETS_URL', ''),
            user=user,
            **ctx
        )
        email.send_email(user.email, body)
        app.logger.info("Sent %s email to user %s <%s>",
                        template.name[:-5], user.id, user.email)
    except Exception as e:
        app.logger.error("Problem sending email to user %s: %s", user.id, e)


def create_registration_emails(date_from=None, date_to=None):
    registration_window = User.query.filter(User.email != '')
    if date_from:
        registration_window = registration_window.filter(User.date_joined >= date_from)
    if date_to:
        registration_window = registration_window.filter(User.date_joined < date_to)

    template = email.env.get_template('welcome.html')
    for user in registration_window:
        _send_email_or_log(user, template)


def _reactivation_feed_context(user, date_from):
    ctx = {}
    videos_per_channel = app.config.get('REACTIVATION_VIDEOS_PER_CHANNEL', 2)
    max_channels = app.config.get('REACTIVATION_MAX_CHANNELS', 3)
    feed = UserContentFeed.query.filter(
        UserContentFeed.user == user.id,
        UserContentFeed.date_added > date_from,
    )

    # Get most recent channels with a least 2 videos in user's feed
    video_channels = dict(
        feed.filter(
            UserContentFeed.video_instance.isnot(None)
        ).group_by(
            UserContentFeed.channel
        ).order_by(
            desc(func.count() > videos_per_channel),
            desc(func.max(UserContentFeed.date_added))
        ).limit(max_channels).values(UserContentFeed.channel, func.count())
    )
    for channel, video_count in video_channels.items():
        videos = list(
            VideoInstance.query.join(
                UserContentFeed,
                (UserContentFeed.video_instance == VideoInstance.id) &
                (UserContentFeed.user == user.id) &
                (UserContentFeed.channel == channel)
            ).
            order_by(desc(UserContentFeed.date_added)).
            limit(videos_per_channel)
        )
        if videos:
            ctx.setdefault('video_data', []).append(
                (videos[0].video_channel, video_count, videos))

    # Get recently created channels from feed (that haven't been used above)
    feed_channels = feed.filter(UserContentFeed.video_instance.is_(None))
    new_channels = list(Channel.query.filter(
        Channel.id.in_(feed_channels.with_entities(UserContentFeed.channel)),
        Channel.id.notin_(video_channels)).limit(max_channels))
    if new_channels:
        ctx['new_channels'] = new_channels

    return ctx


def create_reactivation_emails(date_from=None, date_to=None):
    # select users who became inactive N days ago
    listid = app.config.get('REACTIVATION_EMAIL_LISTID', 1)
    delta = timedelta(days=app.config.get('REACTIVATION_THRESHOLD_DAYS', 7))
    window = [d - delta for d in date_from, date_to]
    inactivity_window = UserAccountEvent.query.group_by(UserAccountEvent.user).\
        having(func.max(UserAccountEvent.event_date).between(*window)).\
        with_entities(UserAccountEvent.user)
    excluded_users = UserFlag.query.filter(
        UserFlag.flag.in_(('bouncing', 'unsub%d' % listid))).with_entities(UserFlag.user)
    inactive_users = User.query.filter(
        User.is_active == True,
        User.email != '',
        User.id.in_(inactivity_window),
        User.id.notin_(excluded_users))

    tracking_params = app.config.get('REACTIVATION_EMAIL_TRACKING_PARAMS')
    with url_tracking_context(tracking_params):
        template = email.env.get_template('reactivation.html')
        for user in inactive_users:
            ctx = _reactivation_feed_context(user, window[0])
            if ctx:
                ctx.update(
                    unsubscribe_token=create_unsubscribe_token(listid, user.id),
                    **tracking_params
                )
                _send_email_or_log(user, template, **ctx)


def _post_facebook_story(user, object_type, object_id, token, action, explicit=False):
    url = ShareLink.create(user, object_type, object_id).url
    if action.startswith('og'):
        post_args = dict(object=url)
    elif object_type == 'channel':
        post_args = dict(channel=url)
    else:
        post_args = dict(other=url)
    if explicit:
        post_args['fb:explicitly_shared'] = 'true'
    try:
        facebook.GraphAPI(token).request('me/' + action, post_args=post_args)
    except:
        app.logger.exception('Failed to autoshare: %s %s', user, object_id)
    else:
        app.logger.info('Autoshare: %s %s', user, object_id)


def send_facebook_likes(date_from, date_to):
    # For all star actions in this activity window, check that the associated user
    # has a valid Facebook publish_actions token and has facebook_autopost_star enabled.
    activity = UserActivity.query.filter(
        UserActivity.action == 'star',
        UserActivity.date_actioned.between(date_from, date_to)
    ).join(
        UserFlag,
        (UserFlag.flag == 'facebook_autopost_star') &
        (UserFlag.user == UserActivity.user)
    ).join(
        ExternalToken,
        (ExternalToken.user == UserActivity.user) &
        (ExternalToken.external_system == 'facebook') &
        (ExternalToken.expires > func.now()) &
        (ExternalToken.permissions.like('%publish_actions%'))
    ).with_entities(UserActivity.user, UserActivity.object_type, UserActivity.object_id,
                    ExternalToken.external_token)
    for user, object_type, object_id, token in activity:
        _post_facebook_story(user, object_type, object_id, token, 'og.likes')


def send_facebook_adds(date_from, date_to):
    # For all videos added in this activity window, check that the channel owner
    # has a valid Facebook publish_actions token and has facebook_autopost_add enabled.
    activity = VideoInstance.query.filter(
        VideoInstance.date_added.between(date_from, date_to)
    ).join(
        Channel,
        (Channel.id == VideoInstance.channel) &
        (Channel.favourite == False)
    ).join(
        UserFlag,
        (UserFlag.flag == 'facebook_autopost_add') &
        (UserFlag.user == Channel.owner)
    ).join(
        ExternalToken,
        (ExternalToken.user == Channel.owner) &
        (ExternalToken.external_system == 'facebook') &
        (ExternalToken.expires > func.now()) &
        (ExternalToken.permissions.like('%publish_actions%'))
    ).with_entities(Channel.owner, VideoInstance.id, ExternalToken.external_token)
    action = app.config['FACEBOOK_APP_NAMESPACE'] + ':add'
    for user, object_id, token in activity:
        _post_facebook_story(user, 'video_instance', object_id, token, action, explicit=True)


def _invalidate_apns_tokens():
    con = push_client.get_feedback_connection()
    srv = push_client.APNs(con, tail_timeout=10)

    device_tokens = []
    for token, since in srv.feedback():
        device_tokens.append(token)
        app.logger.info("AON device token %s is unavailable since %s", token, since)

    if device_tokens:
        updated = ExternalToken.query.filter(
            ExternalToken.external_token.in_(device_tokens),
            ExternalToken.external_system == 'apns'
        ).update({ExternalToken.external_token: 'INVALID'}, synchronize_session=False)

        app.logger.info('%d APN device tokens invalidated', updated)

"""
def set_normalised_values():
    target = 1.0

    norm_e = (e - e_min) / (e_max - e_min)

    ConstantMetrics(
        name='normalised_subscribers',
        value=target/Subscription.query.filter().count()
    )
    ConstantMetrics(
        name='normalised_likes',
        value=target/(UserActivity.query.filter_by(action='star').count() - UserActivity.query.filter_by(action='unstar').count())
    )
"""


@manager.cron_command(interval=604800)  # run weekly
def update_apns_tokens():
    _invalidate_apns_tokens()


@manager.cron_command(interval=300)
@job_control
def update_user_notifications(date_from, date_to):
    """Update user notifications based on recent activity."""
    user_notifications = {}
    create_new_activity_notifications(date_from, date_to, user_notifications)
    create_new_registration_notifications(date_from, date_to, user_notifications)
    create_new_repack_notifications(date_from, date_to, user_notifications)
    create_unavailable_notifications(date_from, date_to, user_notifications)
    create_commmenter_notification(date_from, date_to, user_notifications)
    remove_old_notifications()
    # apns needs the notification ids, so we need to
    # commit first before we continue
    db.session.commit()
    for user in user_notifications.keys():
        send_push_notifications(user)


@manager.cron_command(interval=300)
@job_control
def update_user_content_feed(date_from, date_to):
    """Update users content feed based on recent content changes."""
    create_new_video_feed_items(date_from, date_to)
    create_new_channel_feed_items(date_from, date_to)
    update_video_feed_item_stars(date_from, date_to)
    remove_old_feed_items()


@manager.cron_command(interval=300)
@job_control
def send_registration_emails(date_from, date_to):
    """Send welcome emails to recently registered users."""
    create_registration_emails(date_from, date_to)


@manager.cron_command(interval=900)
@job_control
def send_reactivation_emails(date_from, date_to):
    """Send email to users who haven't been active recently."""
    create_reactivation_emails(date_from, date_to)


@manager.cron_command(interval=60)
@job_control
def process_facebook_autosharing(date_from, date_to):
    """Check for activity by users who have auto-share enabled and post to Facebook."""
    send_facebook_likes(date_from, date_to)
    send_facebook_adds(date_from, date_to)


@manager.cron_command(interval=900)
@job_control
def process_broadcast_messages(date_from, date_to):
    """Send out scheduled broadcast messages."""
    messages = BroadcastMessage.query.filter(
        (BroadcastMessage.date_scheduled.between(date_from, date_to)) &
        (BroadcastMessage.date_processed == None)
    )
    for message in messages:
        users = User.query.filter_by(is_active=True)
        url = message.url_target and BroadcastMessage.get_target_resource_url(message.url_target)
        if message.filter:
            for expr, type, values in BroadcastMessage.parse_filter_string(message.filter):
                if type == 'email':
                    users = users.filter(User.email.like('%%%s' % values))
                if type == 'locale':
                    users = users.filter(User.locale.like('%s%%' % values))
                if type == 'gender':
                    users = users.filter(User.gender == values[0])
                if type == 'age':
                    users = users.filter(between(
                        func.age(User.date_of_birth),
                        text("interval '%s years'" % values[0]),
                        text("interval '%s years'" % values[1])))
                if type == 'subscribed':
                    users = users.join(Subscription,
                                       (Subscription.user == User.id) &
                                       (Subscription.channel == values[0]))

        if message.external_system == 'apns':
            users = users.join(
                ExternalToken,
                (ExternalToken.external_system == 'apns') &
                (ExternalToken.user == User.id)
            ).order_by(ExternalToken.external_token).\
                values(User.id, ExternalToken.external_token)
            _process_apns_broadcast(users, message.message, url)

        app.logger.info('Processed broadcast message: %s', message.label)
        message.date_processed = datetime.utcnow()
        message.save()  # commit now that this message has been processed


@manager.cron_command(interval=3600)
@job_control
def update_user_interests(date_from, date_to):
    active_users = readonly_session.query(UserActivity.user).filter(
        UserActivity.date_actioned.between(date_from, date_to)).subquery()
    activity_categories = readonly_session.query(
        UserActivity.user,
        Channel.category,
        func.count(func.distinct(Channel.id))
    ).outerjoin(
        VideoInstance,
        (UserActivity.object_type == 'video_instance') &
        (UserActivity.object_id == VideoInstance.id)
    ).filter(
        ((UserActivity.object_type == 'channel') & (UserActivity.object_id == Channel.id)) |
        (VideoInstance.channel == Channel.id)
    ).filter(
        UserActivity.user.in_(active_users),
        Channel.category != None
    ).group_by('1, 2').order_by('1, 3 desc')

    for user, categories in groupby(activity_categories, lambda x: x[0]):
        UserInterest.query.filter_by(user=user).delete()
        db.session.execute(UserInterest.__table__.insert(), [
            dict(user=user, explicit=False, category=category, weight=weight)
            for user, category, weight in categories
        ][:10])


def _post_activity_to_recommender(date_from, date_to):
    weights = (
        (UserActivity.action == 'subscribe', 10),
        (UserActivity.action == 'star', 5),
        (UserActivity.action == 'select', 5),
        (UserActivity.action == 'unsubscribe', -5),
    )
    activity = readonly_session.query(
        UserActivity.user,
        Channel.id,
        case(weights, else_=1)
    ).outerjoin(
        VideoInstance,
        (UserActivity.object_type == 'video_instance') &
        (UserActivity.object_id == VideoInstance.id)
    ).filter(
        ((UserActivity.object_type == 'channel') & (UserActivity.object_id == Channel.id)) |
        (VideoInstance.channel == Channel.id)
    )
    if date_from:
        activity = activity.filter(UserActivity.date_actioned.between(date_from, date_to))
    from rockpack.mainsite.core import recommender
    recommender.load_activity(activity.yield_per(1000))


@manager.command
def init_recommender():
    _post_activity_to_recommender(None, None)


@manager.cron_command(interval=120)
@job_control
def update_recommender(date_from, date_to):
    _post_activity_to_recommender(date_from, date_to)


@manager.cron_command(interval=900)
@job_control
def update_user_subscriber_counts(date_from=None, date_to=None):
    """Update subscriber_count on users."""
    users = User.query.join(
        Channel,
        (Channel.owner == User.id) & (Channel.date_updated.between(date_from, date_to)))
    for user in users.distinct():
        # Each user done seperately so that the ES signal kicks in
        user.subscriber_count = Subscription.query.join(
            Channel,
            (Channel.id == Subscription.channel) & (Channel.owner == user.id)
        ).value(func.count(distinct(Subscription.user)))


@manager.cron_command(interval=900)
@job_control
def reset_expiring_tokens(date_from, date_to):
    """Reset the refresh token of a user if their facebook tokens are expiring."""
    # In order to get a new facebook token we need to force the user to reconnect/relogin
    # rockpack with their facebook account.  To do so we force them to logout by changing
    # their refresh_token.
    users = User.query.filter_by(is_active=True).join(
        ExternalToken,
        (ExternalToken.user == User.id) &
        (ExternalToken.external_system == 'facebook') &
        (ExternalToken.expires.between(date_from + timedelta(1), date_to + timedelta(1)))
    )
    count = 0
    for user in users:
        user.reset_refresh_token()
        count += 1
    app.logger.info('Reset refresh token for %d users', count)


@manager.command
@commit_on_success
def fix_invalid_facebook_tokens():
    updated_count = reset_count = 0
    tokens = ExternalToken.query.filter(
        ExternalToken.external_system == 'facebook',
        ExternalToken.expires >= '4001-01-01'
    ).join(
        User,
        (User.id == ExternalToken.user) &
        (User.date_joined < func.now() - text("interval '60 days'"))
    )
    for token in tokens:
        data = facebook.validate_token(
            token.external_token,
            app.config['FACEBOOK_APP_ID'],
            app.config['FACEBOOK_APP_SECRET'])
        if data and 'error' not in data and data['is_valid']:
            assert token.external_uid == str(data['user_id']), repr((token.external_uid, data['user_id']))
            token.expires = datetime.fromtimestamp(data['expires_at'])
            token.permissions = ','.join(data['scopes'])
            updated_count += 1
        else:
            if data and 'error' in data:
                app.logger.info('%s: %s', token.user, data['error'])
            token.expires = '3001-01-01'    # Don't reset this user again
            token.user_rel.reset_refresh_token()
            reset_count += 1
        time.sleep(0.1)     # Don't DOS the facebook service
    app.logger.info('Updated token for %d users', updated_count)
    app.logger.info('Reset refresh token for %d users', reset_count)


@manager.command
def delete_user(username):
    """Mark a user as inactive and delete their channels."""
    user = User.query.filter_by(username=username).one()
    for channel in user.channels:
        channel.deleted = True
        channel.save()
    user.is_active = False
    user.save()
