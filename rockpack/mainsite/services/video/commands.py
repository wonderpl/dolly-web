import time
import logging
from datetime import datetime
from sqlalchemy import func, text, TIME
from rockpack.mainsite import app
from rockpack.mainsite.manager import manager
from rockpack.mainsite.core.dbapi import commit_on_success
from rockpack.mainsite.core.youtube import batch_query, _parse_datetime
from rockpack.mainsite.services.base.models import JobControl
from rockpack.mainsite.services.user.models import Subscription
from rockpack.mainsite.services.video.models import Channel, Video, VideoInstance


@commit_on_success
def set_update_frequency(time_from=None, time_to=None):
    # For each channel, select average number of video instances per week
    # for last 4 weeks and only if added a day after the channel was created
    interval_weeks = app.config.get('UPDATE_FREQUENCY_INTERVAL_WEEKS', 4)
    freq = VideoInstance.query.\
        with_entities(func.count('*') / float(interval_weeks)).\
        filter(VideoInstance.channel == Channel.id).\
        filter(VideoInstance.date_added > func.now() - text("interval '%d weeks'" % interval_weeks)).\
        filter(VideoInstance.date_added > Channel.date_added + text("interval '1 day'"))

    channels = Channel.query
    if time_from and time_to:
        channels = channels.filter(func.cast(Channel.date_added, TIME).between(time_from, time_to))
    channels.update(
        {
            Channel.update_frequency: freq.as_scalar(),
            Channel.date_updated: Channel.date_updated,     # override column onupdate
        }, False)


@commit_on_success
def set_subscription_update_frequency(time_from=None, time_to=None):
    # For each channel, select average number of subscriptions per week
    # for last 4 weeks and only if added a day after the channel was created
    interval_weeks = app.config.get('UPDATE_FREQUENCY_INTERVAL_WEEKS', 4)
    freq = Subscription.query.\
        with_entities(func.count('*') / float(interval_weeks)).\
        filter(Subscription.channel == Channel.id).\
        filter(Subscription.date_created > func.now() - text("interval '%d weeks'" % interval_weeks)).\
        filter(Subscription.date_created > Channel.date_added + text("interval '1 day'"))

    channels = Channel.query
    if time_from and time_to:
        channels = channels.filter(func.cast(Channel.date_added, TIME).between(time_from, time_to))
    channels.update(
        {
            Channel.subscriber_frequency: freq.as_scalar(),
            Channel.date_updated: Channel.date_updated,     # override column onupdate
        }, False)


@manager.cron_command
def update_channel_stats():
    """Update statistics for channels."""
    job_control = JobControl.query.get('update_channel_stats')
    now = datetime.now()
    logging.info('update_channel_stats: from %s to %s', job_control.last_run, now)

    set_update_frequency(job_control.last_run.time(), now.time())

    job_control.last_run = now
    job_control.save()


@manager.cron_command
def update_subscriber_stats():
    """Update statistics for channel."""
    JOB_NAME = 'update_subscriber_stats'
    job_control = JobControl.query.get(JOB_NAME)
    now = datetime.now()
    if not job_control:
        job_control = JobControl(job=JOB_NAME)
        job_control.last_run = now
    logging.info('%s: from %s to %s', JOB_NAME, job_control.last_run, now)

    set_subscription_update_frequency(job_control.last_run.time(), now.time())

    job_control.last_run = now
    job_control.save()


@manager.command
def update_video_data():
    """Query youtube for updated video data."""
    start = '2013-06-08'    # datetime.now()
    fields = 'atom:entry(batch:status,atom:id,atom:author(name),atom:published)'
    while True:
        videos = dict((v.source_videoid, v) for v in
                      Video.query.filter(Video.date_updated < start).limit(50))
        if not videos:
            break
        feed_ids = [('videos', id) for id in videos.keys()]
        for entry in batch_query(feed_ids, dict(fields=fields)).entry:
            id = entry.id.text[-11:]
            videos[id].date_updated = datetime.now()
            if entry.batch_status.code == '200':
                videos[id].source_username = entry.author[0].name.text
                videos[id].date_published = _parse_datetime(entry.published.text)
            elif entry.batch_status.code == '404':
                logging.error('Failed to update %s: %s', id, entry.batch_status.reason)
                if not videos[id].source_username:
                    videos[id].source_username = 'Unknown'
                videos[id].visible = False
            else:
                logging.warning('%s: %s', id, entry.batch_status.reason)
                time.sleep(1)
        Video.query.session.commit()
        time.sleep(60)
