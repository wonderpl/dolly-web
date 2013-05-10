import logging
from datetime import datetime, timedelta
from flask import json
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from rockpack.mainsite import app
from rockpack.mainsite.manager import manager
from rockpack.mainsite.core.dbapi import commit_on_success
from rockpack.mainsite.services.base.models import JobControl
from rockpack.mainsite.services.user.models import UserActivity, UserNotification
from rockpack.mainsite.services.video.models import Channel, VideoInstance


def activity_user(activity):
    # NOTE: This will store full image urls in database
    return dict(
        id=activity.actor.id,
        resource_url=activity.actor.get_resource_url(),
        display_name=activity.actor.display_name,
        avatar_thumbnail_url=activity.actor.avatar.thumbnail_small,
    )


def subscribe_message(activity, channel):
    return channel.owner, 'subscribed', dict(
        user=activity_user(activity),
        channel=dict(
            id=channel.id,
            resource_url=channel.get_resource_url(True),
            thumbnail_url=channel.cover.thumbnail_small,
        )
    )


def star_message(activity, video_instance):
    channel = video_instance.video_channel
    return channel.owner, 'starred', dict(
        user=activity_user(activity),
        video=dict(
            id=video_instance.id,
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


@commit_on_success
def create_new_notifications(date_from=None, date_to=None):
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
                logging.info('read activity %d: %s: %s', activity.id, action, getattr(object, 'id', None))
                if object:
                    user, type, body = get_message(activity, object)
                    UserNotification.query.session.add(UserNotification(
                        user=user,
                        date_created=activity.date_actioned,
                        message_type=type,
                        message=json.dumps(body, separators=(',', ':')),
                    ))


@commit_on_success
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
    logging.info('deleted %d notifications', count)


@manager.cron_command
def update_user_notifications():
    """Update user notifications based on recent activity."""
    job_control = JobControl.query.get('update_user_notifications')
    now = datetime.now()
    logging.info('update_user_notifications: from %s to %s', job_control.last_run, now)

    create_new_notifications(job_control.last_run, now)
    remove_old_notifications()

    job_control.last_run = now
    job_control.save()