import time
import re
import urlparse
from itertools import izip_longest, groupby
from datetime import datetime, timedelta
from flask import json
from sqlalchemy import func, text, case, desc, distinct
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
from rockpack.mainsite.services.share.models import ShareLink
from rockpack.mainsite.services.video.models import (
    Channel, VideoInstanceComment, VideoInstance, Video, Category, ParentCategory)
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
        title=video_instance.video_rel.title,
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


def _process_apns_broadcast(users, alert, url=None, tracking_code=None):
    # Fake notification id passed because iOS app won't follow url without it :-(
    message = dict(alert=alert, id=0)
    if url:
        message['url'] = _apns_url(url)
    if tracking_code:
        message['tracking_code'] = tracking_code
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


def complex_push_notification(token, push_message, push_message_args, **kwargs):
    message = dict(
        alert={
            "loc-key": push_message,
            "loc-args": push_message_args
        }
    )
    message.update(kwargs)
    for key, value in message.iteritems():
        if value is None:
            del message[key]
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

    notifications = UserNotification.query.filter_by(date_read=None, user=user_id)
    count = notifications.value(func.count())
    app.logger.debug('%s notification count: %d', user_id, count)

    # Send most recent notification only, if we have configuration for it
    notification_map = app.config['PUSH_NOTIFICATION_MAP']
    notification = notifications.filter(
        UserNotification.message_type.in_(notification_map.keys())
    ).order_by('id desc').first()
    if not notification:
        return
    data = json.loads(notification.message)
    key, push_message = notification_map[notification.message_type]
    deeplink_url = _apns_url(data[key]['resource_url'])

    try:
        push_message_args = [data['user']['display_name']]
    except KeyError:
        push_message_args = []

    return complex_push_notification(
        token, push_message, push_message_args,
        badge=count, id=notification.id, url=deeplink_url,
        tracking_code='apns %s' % notification.message_type)


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
        if user_notifications is not None and message_type in app.config['PUSH_NOTIFICATION_MAP']:
            user_notifications.setdefault(user, None)


def influencer_starred_email(recipient, sender, infuencer_id, video_instance):
    listid = app.config.get('RECOMMENDATION_EMAIL_LISTID', 2)
    if any(f for f in recipient.flags if f.flag in ('bouncing', 'unsub%d' % listid)):
        return
    influencer = User.query.get(infuencer_id)
    link = ShareLink.create(sender.id, 'video_instance', video_instance.id)
    ctx = dict(
        sender=sender,
        link=link,
        object_type='video_instance',
        object_type_name='video',
        object=video_instance,
        senders=[sender, influencer],
        unsubscribe_token=create_unsubscribe_token(listid, recipient.id)
    )
    tracking_params = app.config.get('RECOMMENDATION_EMAIL_TRACKING_PARAMS')
    with url_tracking_context(tracking_params):
        template = email.env.get_template('video_recommendation.html')
        _send_email_or_log(recipient, template, **ctx)


def influencer_starred_activity(userid, videoid):
    UserActivity(
        user=userid,
        action='recommended',
        object_type='video',
        object_id=videoid,
        tracking_code=None
    ).add()


@commit_on_success
def recommend_for_influencers(instance_id, user_id):
    user = User.query.get(user_id)
    if user and not user.is_influencer:
        instance = VideoInstance.query.get(instance_id)
        if not instance:
            app.logger.warning('Invalid instance_id %s', instance_id)
            return

        influencer_videos = dict(
            VideoInstance.query.join(
                Channel,
                (Channel.id == VideoInstance.channel) &
                (Channel.public == True)
            ).join(
                User,
                (User.id == Channel.owner) &
                (User.is_influencer == True)
            ).filter(
                VideoInstance.video == instance.video
            ).values(VideoInstance.video, User.id)
        )

        if influencer_videos:
            subscription_friend = Channel.query.\
                join(Subscription, Subscription.channel == Channel.id).\
                filter(Subscription.user == user.id).\
                with_entities(Channel.owner.label('friendid'), Subscription.user.label('userid'))

            email_friend = ExternalFriend.query.\
                join(User,
                     (ExternalFriend.email == User.email) &
                     (ExternalFriend.external_system == 'email')).\
                filter(ExternalFriend.user == user.id).\
                with_entities(User.id.label('friendid'),
                              ExternalFriend.user.label('userid'))

            external_friend = ExternalToken.query.\
                join(ExternalFriend,
                     (ExternalFriend.external_system == ExternalToken.external_system) &
                     (ExternalFriend.external_uid == ExternalToken.external_uid)).\
                filter(ExternalFriend.user == user.id).\
                with_entities(ExternalToken.user.label('friendid'),
                              ExternalFriend.user.label('userid'))

            unioned = subscription_friend.union_all(email_friend, external_friend).subquery()

            # Fetch the user's friends to email
            friends = User.query.join(
                unioned,
                unioned.c.friendid == User.id
            ).filter(
                User.email != ''
            ).outerjoin(
                UserActivity,
                (UserActivity.user == User.id) &
                (
                    (
                        (UserActivity.object_type == 'video_instance') &
                        (UserActivity.action == 'view')
                    ) |
                    (
                        (UserActivity.object_type == 'video') &
                        (UserActivity.action == 'recommended')
                    )
                ) &
                (UserActivity.user == unioned.c.friendid)
            ).outerjoin(
                VideoInstance,
                (VideoInstance.video == instance.video) &
                (
                    (VideoInstance.id == UserActivity.object_id) |
                    (VideoInstance.video == UserActivity.object_id)
                )
            ).group_by(User.id).with_entities(User, func.count(VideoInstance.video))

            for friend, count in friends:
                if count == 0:
                    influencer_starred_email(
                        friend, user, influencer_videos[instance.video], instance)
                    influencer_starred_activity(friend.id, instance.video)


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
        if user_notifications is not None and type in app.config['PUSH_NOTIFICATION_MAP']:
            user_notifications.setdefault(packer_channel.owner, None)


def create_influencer_notifications(date_from=None, date_to=None, user_notifications=None):
    activity = UserActivity.query.filter(
        UserActivity.date_actioned.between(date_from, date_to),
        UserActivity.action == 'star',
    )

    for instance_id, user_id in activity.values(UserActivity.object_id, UserActivity.user):
        recommend_for_influencers(instance_id, user_id)


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
                    if user_notifications is not None and type in app.config['PUSH_NOTIFICATION_MAP']:
                        user_notifications.setdefault(user, None)


def create_new_registration_notifications(date_from=None, date_to=None, user_notifications=None):
    new_users = User.query.join(ExternalToken, (
        (ExternalToken.user == User.id) &
        (ExternalToken.external_system != 'apns'))
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
            if user_notifications is not None and message_type in app.config['PUSH_NOTIFICATION_MAP']:
                user_notifications.setdefault(friend, None)

    if app.config.get('DOLLY'):

        FriendUser = aliased(User)

        new_email_users = User.query.join(
            ExternalFriend,
            (ExternalFriend.email == User.email) &
            (ExternalFriend.external_system == 'email')
        ).join(
            FriendUser,
            ExternalFriend.user == FriendUser.id
        ).with_entities(FriendUser.id, User)

        if date_from:
            new_email_users = new_email_users.filter(User.date_joined >= date_from)

        if date_to:
            new_email_users = new_email_users.filter(User.date_joined < date_to)

        for friend, user in new_email_users:
            friend, message_type, message = joined_message(friend, user)
            _add_user_notification(friend, user.date_joined, message_type, message)
            if user_notifications is not None and message_type in app.config['PUSH_NOTIFICATION_MAP']:
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
                if user_notifications is not None and type in app.config['PUSH_NOTIFICATION_MAP']:
                    user_notifications.setdefault(user.id, None)


def check_share_notifications(date_from, date_to, user_notifications=None):
    # The share notification records are created in share.api.share_content
    # but we check here if any should trigger a push notification.
    for type in 'channel_shared', 'video_shared':
        if user_notifications is not None and type in app.config['PUSH_NOTIFICATION_MAP']:
            user_notifications.update(
                UserNotification.query.filter(
                    UserNotification.date_created >= date_from,
                    UserNotification.date_created < date_to,
                    UserNotification.message_type == type
                ).values(UserNotification.user, UserNotification.message_type)
            )


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

    subscription_friend = Channel.query.\
        join(Subscription, Subscription.channel == Channel.id).\
        with_entities(Channel.owner.label('friendid'), Subscription.user.label('userid'))

    email_friend = ExternalFriend.query.\
        join(User,
             (ExternalFriend.email == User.email) &
             (ExternalFriend.external_system == 'email')).\
        with_entities(User.id.label('friendid'),
                      ExternalFriend.user.label('userid'))

    external_friend = ExternalToken.query.\
        join(ExternalFriend,
             (ExternalFriend.external_system == ExternalToken.external_system) &
             (ExternalFriend.external_uid == ExternalToken.external_uid)).\
        with_entities(ExternalToken.user.label('friendid'),
                      ExternalFriend.user.label('userid'))

    unioned = subscription_friend.union_all(email_friend, external_friend).subquery()

    feed_items = UserContentFeed.query.\
        join(UserActivity,
             (UserActivity.action == 'star') &
             (UserActivity.date_actioned.between(date_from, date_to))).\
        join(unioned, unioned.c.userid == UserContentFeed.user).\
        filter((UserActivity.user == unioned.c.friendid) &
               (UserContentFeed.user != UserActivity.user) &
               (UserContentFeed.video_instance == UserActivity.object_id)).\
        with_entities(UserContentFeed, func.string_agg(UserActivity.user, ' ')).\
        group_by(UserContentFeed.id)

    star_limit = app.config.get('FEED_STARS_LIMIT', 3)
    for feed_item, new_stars in feed_items:
        old_stars = json.loads(feed_item.stars) if feed_item.stars else []
        new_stars = [l for l in set(new_stars.split()) if l not in old_stars]
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

    [
        notify_users.update({user: token}) for user, token in
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


def create_ping_emails(listid, template_path, threshold_days, tracking_params, date_from=None, date_to=None):
    delta = timedelta(days=threshold_days)
    window = [d - delta for d in date_from, date_to]
    excluded_users = UserFlag.query.filter(
        UserFlag.flag.in_(('bouncing', 'unsub%d' % listid))).with_entities(UserFlag.user)
    users = User.query.filter(
        User.is_active == True,
        User.email != '',
        User.date_joined.between(*window),
        User.id.notin_(excluded_users))

    with url_tracking_context(tracking_params):
        template = email.env.get_template(template_path)
        for user in users:
            ctx = dict(
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
    if app.config.get('DOLLY'):
        create_influencer_notifications(date_from, date_to, user_notifications)
    else:
        create_new_activity_notifications(date_from, date_to, user_notifications)
        create_new_repack_notifications(date_from, date_to, user_notifications)
        create_unavailable_notifications(date_from, date_to, user_notifications)
    create_new_registration_notifications(date_from, date_to, user_notifications)
    create_commmenter_notification(date_from, date_to, user_notifications)
    check_share_notifications(date_from, date_to, user_notifications)
    remove_old_notifications()
    # apns needs the notification ids, so we need to
    # commit first before we continue
    db.session.commit()
    for user in user_notifications.keys():
        try:
            send_push_notifications(user)
        except:
            # Don't repeat this cron command if this fails
            app.logger.exception('Failed to send push notifications for %s', user)


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
    if app.config['REACTIVATION_THRESHOLD_DAYS']:
        create_reactivation_emails(date_from, date_to)
    ping_emails = app.config.get('PING_EMAILS', [])
    for config in ping_emails:
        config.update(date_from=date_from, date_to=date_to)
        create_ping_emails(**config)


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
        url = message.url_target and BroadcastMessage.get_target_resource_url(message.url_target)

        if message.external_system == 'apns':
            users = message.get_users().values(User.id, ExternalToken.external_token)
            _process_apns_broadcast(users, message.message, url,
                                    tracking_code='apns bcast %d' % message.id)

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


@commit_on_success
def update_user_counts(subscribe_counts):
    for owner_id, count in subscribe_counts:
        db.session.query(User).filter(User.id == owner_id).\
            update({"subscriber_count": count})


@manager.cron_command(interval=900)
@job_control
def update_user_subscriber_counts(date_from=None, date_to=None):
    """Update subscriber_count on users."""

    subscribe_counts = Subscription.query.join(Channel, (Channel.id == Subscription.channel))

    if date_from:
        subscribed_channels = Subscription.query.filter(
            Subscription.date_created.between(date_from, date_to)
        ).with_entities(distinct(Subscription.channel)).subquery()

        subscribe_counts = subscribe_counts.filter(
            Subscription.channel.in_(subscribed_channels))

    subscribe_counts = subscribe_counts.group_by(
        Channel.owner
    ).with_entities(Channel.owner, func.count(distinct(Subscription.user)))

    update_user_counts(subscribe_counts)


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


@manager.command
def load_users_into_mailchimp():
    """Load records from user table to mailchimp list."""
    from mailchimp import Mailchimp
    excluded_users = UserFlag.query.filter(
        UserFlag.flag.in_(('bouncing', 'unsub3'))).with_entities(UserFlag.user)
    users = readonly_session.query(
        User.id,
        User.username,
        User.email,
        User.first_name,
        User.last_name,
        User.gender,
        User.locale,
        User.date_joined,
        ParentCategory.name.label('interest_name'),
        func.sum(UserInterest.weight).label('interest_weight'),
    ).filter(
        User.is_active == True,
        User.email != '',
        User.id.notin_(excluded_users),
    ).outerjoin(
        UserInterest, UserInterest.user == User.id
    ).outerjoin(
        Category, Category.id == UserInterest.category
    ).outerjoin(
        ParentCategory, ParentCategory.id == Category.parent
    ).group_by(
        User.id, ParentCategory.id
    )
    # TODO: chunking
    batch = []
    for userid, group in groupby(users.order_by(User.id), lambda u: u[0]):
        usergroup = list(group)
        user = usergroup[0]
        merge_vars = dict(
            fname=user.first_name,
            lname=user.last_name,
            username=user.username,
            gender={'m': 'Male', 'f': 'Female'}.get(user.gender, 'Unknown'),
            locale=user.locale,
            datejoined=datetime.strftime(user.date_joined, '%m/%d/%Y'),
        )
        interests = [u.interest_name for u in usergroup if u.interest_name]
        if interests:
            merge_vars['groupings'] = [dict(name='Interest', groups=interests)]
        batch.append(dict(
            email=dict(email=user.email),
            email_type='html',
            merge_vars=merge_vars,
        ))
    conn = Mailchimp(app.config['MAILCHIMP_TOKEN'])
    response = conn.lists.batch_subscribe(
        app.config['MAILCHIMP_LISTID'],
        batch,
        double_optin=False,
        update_existing=True,
        replace_interests=True)
    if response['error_count']:
        app.logger.error('Error loading users into mailchimp: %s', response['errors'][0]['error'])
    else:
        app.logger.info('Loaded users into mailchimp: %d added, %d updated', response['add_count'], response['update_count'])
