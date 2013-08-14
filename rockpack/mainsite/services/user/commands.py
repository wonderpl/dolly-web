import urlparse
from functools import wraps
from datetime import datetime, timedelta
from flask import json
from sqlalchemy import func
from sqlalchemy.orm import joinedload, contains_eager, aliased
from sqlalchemy.orm.exc import NoResultFound
from rockpack.mainsite import app
from rockpack.mainsite.manager import manager
from rockpack.mainsite.core.dbapi import commit_on_success, db
from rockpack.mainsite.core import email
from rockpack.mainsite.core.apns import push_client
from rockpack.mainsite.services.oauth import facebook
from rockpack.mainsite.services.base.models import JobControl
from rockpack.mainsite.services.oauth.models import ExternalFriend, ExternalToken
from rockpack.mainsite.services.video.models import Channel, VideoInstance
from rockpack.mainsite.services.share.models import ShareLink
from .models import User, UserActivity, UserNotification, UserContentFeed, UserFlag, Subscription


def activity_user(activity):
    # NOTE: This will store full image urls in database
    return dict(
        id=activity.actor.id,
        resource_url=activity.actor.get_resource_url(),
        display_name=activity.actor.display_name,
        avatar_thumbnail_url=activity.actor.avatar.thumbnail_medium,
    )


def subscribe_message(activity, channel):
    return channel.owner, 'subscribed', dict(
        user=activity_user(activity),
        channel=dict(
            id=channel.id,
            resource_url=channel.get_resource_url(True),
            thumbnail_url=channel.cover.thumbnail_medium,
        )
    )


def star_message(activity, video_instance):
    channel = video_instance.video_channel
    return channel.owner, 'starred', dict(
        user=activity_user(activity),
        video=dict(
            id=video_instance.id,
            resource_url=video_instance.resource_url,
            thumbnail_url=video_instance.default_thumbnail,
            channel=dict(
                id=channel.id,
                resource_url=channel.get_resource_url(True),
            )
        )
    )


activity_notification_map = dict(
    # map action -> activity list, object model, message function
    subscribe=([], Channel, subscribe_message),
    star=([], VideoInstance, star_message),
)


# XXX: This assumes that the notifications passed in are not yet
# committed to the db
def send_push_notifications(user):
    try:
        try:
            user_id = user.id
        except:
            user_id = user
        device = ExternalToken.query.filter(
            ExternalToken.external_system == 'apns',
            ExternalToken.external_token != 'INVALID',
            ExternalToken.user == user_id).one()
    except NoResultFound:
        return

    notifications = UserNotification.query.filter_by(date_read=None, user=user_id).order_by('id desc')
    count = notifications.count()
    app.logger.debug('%s notification count: %d', user_id, count)

    # Send most recent notification only
    notification = sorted(notifications, key=lambda n: n.id, reverse=True)[0]

    try:
        if notification.message_type == 'subscribed':
            key = 'channel'
            push_message = "%@ has subscribed to your channel"
        elif notification.message_type == 'joined':
            key = 'user'
            push_message = "Your Facebook friend %@ has joined Rockpack"
        else:
            key = 'video'
            push_message = "%@ has liked your video"

        data = json.loads(notification.message)
        name = data['user']['display_name']

        push_message_args = [name]

        extra_kwargs = {}
        if app.config.get('ENABLE_APNS_DEEPLINKS', True):
            extra_kwargs.update(
                dict(
                    url=urlparse.urlparse(data[key]['resource_url']).path.lstrip('/ws/')
                )
            )

        message = dict(
            alert={
                "loc-key": push_message,
                "loc-args": push_message_args,
            },
            badge=count,
            id=notification.id,
            **extra_kwargs)

        srv = push_client.APNs(push_client.connection)
        result = srv.send(push_client.Message(device.external_token, **message))
        app.logger.info('Sent message to %s: %r', device.user, message)
        return result
    except Exception:
        app.logger.exception('Failed to send push notification: %d', notification.id)


def create_new_activity_notifications(date_from=None, date_to=None, user_notifications=None):
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
                    notification = UserNotification(
                        user=user,
                        date_created=activity.date_actioned,
                        message_type=type,
                        message=json.dumps(body, separators=(',', ':')),
                    )
                    UserNotification.query.session.add(notification)
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
            message = dict(user=dict(
                id=user.id,
                resource_url=user.resource_url,
                avatar_thumbnail_url=user.avatar.url,
                display_name=user.display_name,
            ))
            notification = UserNotification(
                user=friend,
                date_created=user.date_joined,
                message_type='joined',
                message=json.dumps(message, separators=(',', ':')),
            )
            UserNotification.query.session.add(notification)
            if user_notifications is not None:
                user_notifications.setdefault(friend, None)


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
    for query, U in (sub_channels, Subscription), (friend_channels, ExternalFriend):
        UserContentFeed.query.session.add_all(
            UserContentFeed(user=user, channel=channel, date_added=date_published)
            for user, channel, date_published in
            # use outerjoin to filter existing records
            query.outerjoin(
                UserContentFeed,
                (UserContentFeed.user == U.user) &
                (UserContentFeed.channel == Channel.id) &
                (UserContentFeed.video_instance == None)).
            filter(UserContentFeed.id == None).
            distinct().values(U.user, Channel.id, Channel.date_published)
        )


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


def create_registration_emails(date_from=None, date_to=None):
    registration_window = User.query.filter(User.email != '')
    if date_from:
        registration_window = registration_window.filter(User.date_joined >= date_from)
    if date_to:
        registration_window = registration_window.filter(User.date_joined < date_to)

    subject = 'Welcome to Rockpack'
    template = email.env.get_template('welcome.html')
    for user in registration_window:
        try:
            body = template.render(
                subject=subject,
                username=user.username,
                email=user.email,
                email_sender=app.config['DEFAULT_EMAIL_SOURCE'],
                assets=app.config.get('ASSETS_URL', '')
            )
            email.send_email(user.email, subject, body, format='html')
        except Exception as e:
            app.logger.error("Problem sending registration email for user.id '%s': %s", user.id, str(e))


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
        Channel.id == VideoInstance.channel
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


def job_control(f):
    """Wrap the given function to ensure the input data is limited to a specific interval."""
    @wraps(f)
    @commit_on_success
    def wrapper():
        now = datetime.utcnow()
        job_name = f.__name__
        job_control = JobControl.query.get(job_name)
        if not job_control:
            job_control = JobControl(job=job_name, last_run=now)
        app.logger.info('%s: from %s to %s', job_name, job_control.last_run, now)

        f(job_control.last_run, now)

        # XXX: If the cron function throws an exception then last_run is not saved
        # and the job will be retried next time, including the same interval.
        job_control.last_run = now
        job_control.save()
    return wrapper


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


@manager.cron_command
def update_apns_tokens():
    _invalidate_apns_tokens()


@manager.cron_command
@job_control
def update_user_notifications(date_from, date_to):
    """Update user notifications based on recent activity."""
    user_notifications = {}
    create_new_activity_notifications(date_from, date_to, user_notifications)
    create_new_registration_notifications(date_from, date_to, user_notifications)
    remove_old_notifications()
    # apns needs the notification ids, so we need to
    # commit first before we continue
    db.session.commit()
    for user in user_notifications.keys():
        send_push_notifications(user)


@manager.cron_command
@job_control
def update_user_content_feed(date_from, date_to):
    """Update users content feed based on recent content changes."""
    create_new_video_feed_items(date_from, date_to)
    create_new_channel_feed_items(date_from, date_to)
    update_video_feed_item_stars(date_from, date_to)
    remove_old_feed_items()


@manager.cron_command
@job_control
def send_registration_emails(date_from, date_to):
    """Send an email based on a template."""
    create_registration_emails(date_from, date_to)


@manager.cron_command
@job_control
def process_facebook_autosharing(date_from, date_to):
    """Check for activity by users who have auto-share enabled and post to Facebook."""
    send_facebook_likes(date_from, date_to)
    send_facebook_adds(date_from, date_to)


@manager.command
def delete_user(username):
    """Mark a user as inactive and delete their channels."""
    user = User.query.filter_by(username=username).one()
    for channel in user.channels:
        channel.deleted = True
        channel.save()
    user.is_active = False
    user.save()
