import logging
from datetime import datetime, timedelta
from flask import json
from sqlalchemy import func
from sqlalchemy.orm import joinedload, contains_eager
from rockpack.mainsite import app
from rockpack.mainsite.manager import manager
from rockpack.mainsite.core.dbapi import commit_on_success
from rockpack.mainsite.core import email
from rockpack.mainsite.services.base.models import JobControl
from rockpack.mainsite.services.user.models import UserActivity, UserNotification, User
from rockpack.mainsite.services.oauth.models import ExternalFriend, ExternalToken
from rockpack.mainsite.services.video.models import Channel, VideoInstance


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


from apnsclient import Session as APNSession
from apnsclient import Message as APNMessage
from apnsclient import APNs

import os
from sqlalchemy.orm.exc import NoResultFound


def send_push_notification(user):
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

    notifications = UserNotification.query.filter(
        UserNotification.message_type.in_(['starred', 'subscribed']),
        UserNotification.date_read == None,
        UserNotification.user == user.id
    ).order_by('date_created desc')

    count = notifications.count()

    if count:
        con = APNSession.new_connection(
            app.config['APNS_PUSH_TYPE'],
            cert_file=os.path.dirname(os.path.abspath(__file__)) + "/CertificateAndKey.pem",
            passphrase=app.config['APNS_PASSPHRASE']
        )
        first = notifications.first()

        key = 'user' # defaulting for message_type == subscribed
        notification_for = 'channel'
        action = 'subscribed to'

        if first.message_type == 'starred':
            key = 'video'
            notification_for = 'video'
            action = 'liked'

        data = json.loads(first.message)

        name = data[key]['display_name']

        message = APNMessage(
                device.external_token,
                alert="%s just %s your %s" % (name, action, notification_for),
                badge=count)

        srv = APNs(con)
        return srv.send(message)

    """
    # Retry once
    if response.needs_retry():
        response.retry()
    """


@commit_on_success
def create_new_activity_notifications(date_from=None, date_to=None):
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
                    if user == activity.user:
                        # Don't send notifications to self
                        continue
                    UserNotification.query.session.add(UserNotification(
                        user=user,
                        date_created=activity.date_actioned,
                        message_type=type,
                        message=json.dumps(body, separators=(',', ':')),
                    ))
                    send_push_notification(user)


@commit_on_success
def create_new_registration_notifications(date_from=None, date_to=None):
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
            UserNotification.query.session.add(UserNotification(
                user=friend,
                date_created=user.date_joined,
                message_type='joined',
                message=json.dumps(message, separators=(',', ':')),
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


@manager.cron_command
def update_user_notifications():
    """Update user notifications based on recent activity."""
    job_control = JobControl.query.get('update_user_notifications')
    now = datetime.now()
    logging.info('update_user_notifications: from %s to %s', job_control.last_run, now)

    create_new_activity_notifications(job_control.last_run, now)
    create_new_registration_notifications(job_control.last_run, now)
    remove_old_notifications()

    job_control.last_run = now
    job_control.save()


@manager.cron_command
def send_registration_emails():
    """ Send an email based on a template """
    JOB_NAME = 'send_registration_emails'
    job_control = JobControl.query.get(JOB_NAME)
    now = datetime.utcnow()
    if not job_control:
        job_control = JobControl(job=JOB_NAME)
        job_control.last_run = now
    logging.info('{}: from {} to {}'.format(JOB_NAME, job_control.last_run, now))

    create_registration_emails(job_control.last_run, now)

    job_control.last_run = now
    job_control.save()


@manager.command
def delete_user(username):
    """Mark a user as inactive and delete their channels."""
    user = User.query.filter_by(username=username).one()
    for channel in user.channels:
        channel.deleted = True
        channel.save()
    user.is_active = False
    user.save()
