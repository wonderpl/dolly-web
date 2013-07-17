import time
import logging
from datetime import datetime, timedelta
import pyes
from sqlalchemy import func, text, TIME, distinct, or_
from rockpack.mainsite import app
from rockpack.mainsite.manager import manager
from rockpack.mainsite.core.es import mappings, api
from rockpack.mainsite.core.es import es_connection
from rockpack.mainsite.core.dbapi import commit_on_success
from rockpack.mainsite.core.youtube import batch_query, _parse_datetime
from rockpack.mainsite.services.base.models import JobControl
from rockpack.mainsite.services.user.models import Subscription, UserActivity
from rockpack.mainsite.services.video.models import (
    Channel, ChannelLocaleMeta, ChannelPromotion, Video, VideoInstance, PlayerErrorReport)


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


@commit_on_success
def set_channel_view_count(time_from=None, time_to=None):
    # For each channel, select the total number of users
    # who've made 1 or more actions on a channel per hour
    session = ChannelLocaleMeta.query.session
    for object_type in ('video', 'channel', ):
        ua = None
        ids = {}

        if object_type == 'video':

            ua = UserActivity.query.session.query(
                UserActivity.locale,
                VideoInstance.channel,
                func.count(distinct(UserActivity.user))
            ).filter(
                VideoInstance.id == UserActivity.object_id
            ).group_by(
                UserActivity.locale,
                VideoInstance.channel
            )

        else:
            ua = UserActivity.query.session.query(
                UserActivity.locale,
                UserActivity.object_id,
                func.count(distinct(UserActivity.user))
            ).group_by(
                UserActivity.locale,
                UserActivity.object_id
            )

        ua = ua.filter(
            UserActivity.date_actioned > time_from
        )

        if not ua.count():
            continue

        for u in ua:
            loc, channel, val = u
            ids.setdefault(loc, {}).setdefault(channel, 0)
            ids[loc][channel] += val

        for locale in ids.keys():
            channel_metas = ChannelLocaleMeta.query.filter(ChannelLocaleMeta.locale == locale, ChannelLocaleMeta.channel.in_(ids[locale].keys()))
            for meta in channel_metas:
                meta.view_count += ids[locale][meta.channel]
                session.add(meta)


@manager.cron_command
def update_channel_view_counts():
    """Update view counts for channel."""
    JOB_NAME = 'update_channel_view_stats'
    job_control = JobControl.query.get(JOB_NAME)
    now = datetime.now()
    if not job_control:
        job_control = JobControl(job=JOB_NAME)
        job_control.last_run = now - timedelta(hours=1)
    logging.info('%s: from %s to %s', JOB_NAME, job_control.last_run, now)

    set_channel_view_count(job_control.last_run)
    job_control.last_run = now
    job_control.save()


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


def update_channel_promo_activity():
    # Push everything to es. Promotion data
    # will get updated during insert
    for p in ChannelPromotion.query.all():
        api.add_channel_to_index(p.channel_rel)


@manager.cron_command
def update_channel_promotions():
    """ Update promotion data for channels in ES """
    JOB_NAME = 'update_subscriber_stats'
    job_control = JobControl.query.get(JOB_NAME)
    now = datetime.now()
    if not job_control:
        job_control = JobControl(job=JOB_NAME)
        job_control.last_run = now

    logging.info('%s: from %s to %s', JOB_NAME, job_control.last_run, now)

    update_channel_promo_activity()

    job_control.last_run = now
    job_control.save()


@manager.cron_command
def check_video_player_errors():
    """Scan player error records and check that videos are still available."""
    JOB_NAME = 'check_video_player_errors'
    job_control = JobControl.query.get(JOB_NAME)
    now = datetime.now()
    if not job_control:
        job_control = JobControl(job=JOB_NAME)
        job_control.last_run = now
    logging.info('%s: from %s to %s', JOB_NAME, job_control.last_run, now)

    error_videos = set(v[0] for v in PlayerErrorReport.query.filter(
        PlayerErrorReport.date_updated.between(job_control.last_run, now)).
        join(VideoInstance, VideoInstance.id == PlayerErrorReport.video_instance).
        values('video'))
    if error_videos:
        video_qs = Video.query.filter(Video.id.in_(error_videos))
        get_youtube_video_data(video_qs, now)

    job_control.last_run = now
    job_control.save()


@manager.command
def update_video_data(start):
    """Query youtube for updated video data."""
    #start = '2013-06-08'
    get_youtube_video_data(Video.query, start)


def get_youtube_video_data(video_qs, start):
    fields = 'atom:entry(batch:status,atom:id,atom:author(name),atom:published,yt:noembed)'
    while True:
        videos = dict((v.source_videoid, v) for v in
                      video_qs.filter(Video.date_updated < start).limit(50))
        if not videos:
            break
        feed_ids = [('videos', id) for id in videos.keys()]
        for entry in batch_query(feed_ids, dict(fields=fields)).entry:
            id = entry.id.text[-11:]
            videos[id].date_updated = datetime.now()
            if entry.batch_status.code == '200':
                videos[id].source_username = entry.author[0].name.text
                videos[id].date_published = _parse_datetime(entry.published.text)
                if 'noembed' in [e.tag for e in entry.extension_elements]:
                    logging.warning('%s: marked not visible: noembed', id)
                    videos[id].visible = False
                #group = [e for e in entry.extension_elements if e.tag == 'group'][0]
                #print id, [(c.attributes, c.text) for c in group.children if c.tag == 'restriction']
            elif entry.batch_status.code == '404':
                logging.error('Failed to update %s: %s', id, entry.batch_status.reason)
                if not videos[id].source_username:
                    videos[id].source_username = 'Unknown'
                videos[id].visible = False
            else:
                logging.warning('%s: %s', id, entry.batch_status.reason)
                time.sleep(1)
        Video.query.session.commit()
        if len(videos) == 50:
            time.sleep(60)


@manager.command
def sanitise_es():
    """ Delete channels and videos from ES that shouldn't be present """
    channels = Channel.query.filter(
        or_(
            Channel.public == False,
            Channel.visible == False,
            Channel.deleted == True
        )
    )

    logging.info('Checking channels: %s marked as deleted/private/invisible in db', channels.count())
    count = 0
    for channel in channels.yield_per(6000).values('id'):
        try:
            es_connection.delete(mappings.CHANNEL_INDEX, mappings.CHANNEL_TYPE, channel[0])
        except pyes.exceptions.NotFoundException:
            pass
        else:
            count += 1
    logging.info('Finished channels: %s removed from ES', count)

    es_videos = es_connection.search(
        pyes.MatchAllQuery(),
        mappings.VIDEO_INDEX,
        mappings.VIDEO_TYPE,
        fields=['_id'],
        scan=True,
    )
    es_instance_ids = set(v.get_id() for v in es_videos)
    db_instance_ids = set(v[0] for v in VideoInstance.query.values(VideoInstance.id))
    logging.info('Checking videos: %d in DB, %d in ES', len(db_instance_ids), len(es_instance_ids))
    count = 0
    for id in es_instance_ids - db_instance_ids:
        try:
            es_connection.delete(mappings.VIDEO_INDEX, mappings.VIDEO_TYPE, id)
        except pyes.exceptions.NotFoundException:
            logging.exception('Failed to remove videos: %s', id)
        else:
            count += 1
    logging.info('Finished videos: %s removed from ES', count)
