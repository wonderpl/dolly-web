import re
import time
import logging
from datetime import datetime, timedelta
import pyes
from sqlalchemy import func, text, TIME, distinct, or_
from rockpack.mainsite import app
from rockpack.mainsite.manager import manager, job_control
from rockpack.mainsite.core.es import mappings, api
from rockpack.mainsite.core.es import es_connection, helpers
from rockpack.mainsite.core.dbapi import commit_on_success
from rockpack.mainsite.core.youtube import batch_query, _parse_datetime
from rockpack.mainsite.helpers.http import get_external_resource
from rockpack.mainsite.services.user.models import Subscription, UserActivity, User
from rockpack.mainsite.services.video.models import (
    Channel, ChannelLocaleMeta, UserPromotion, ChannelPromotion,
    Video, VideoInstance, VideoInstanceQueue, PlayerErrorReport)


@manager.cron_command(interval=900)
@job_control
def update_channel_stats(date_from=None, date_to=None):
    """Update frequency stats columns on channel."""
    interval_weeks = app.config.get('UPDATE_FREQUENCY_INTERVAL_WEEKS', 4)
    updates = dict(
        (stats_field,
         # Select averate numbers of items per week
         src_model.query.with_entities(func.count() / float(interval_weeks)).
         # Look at only last N weeks and only if added a day after the channel was created
         filter(
             src_model.channel == Channel.id,
             date_added > func.now() - text("interval '%d weeks'" % interval_weeks),
             date_added > Channel.date_added + text("interval '1 day'")
         ).as_scalar())
        for stats_field, src_model, date_added in (
            (Channel.update_frequency, VideoInstance, VideoInstance.date_added),
            (Channel.subscriber_frequency, Subscription, Subscription.date_created),
        )
    )
    updates[Channel.date_updated] = Channel.date_updated  # override column onupdate

    channels = Channel.query
    if date_from and date_to:
        # Update only those channels created within the time window.
        # All channels should be updated within a 24 hour period.
        channels = channels.filter(func.cast(Channel.date_added, TIME).between(
            date_from.time(), date_to.time()))
    channels.update(updates, False)


@manager.cron_command(interval=3600)
@job_control
def update_channel_view_counts(time_from=None, time_to=None):
    """Update view counts for channel."""
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
            UserActivity.date_actioned.between(time_from, time_to)
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


@manager.cron_command(interval=3600)
def update_channel_rank():
    start = time.time()
    helpers.DBImport().import_channel_share()
    app.logger.info('Ran update_channel_rank in %ds', time.time() - start)


@manager.command
def update_video_channel_terms():
    start = time.time()
    helpers.DBImport().import_video_channel_terms()
    app.logger.info('Ran import_video_channel_terms in %ds', time.time() - start)


@manager.cron_command(interval=900)
@job_control
def update_channel_promotions(date_from=None, date_to=None):
    """ Update promotion data for channels in ES """
    # Push everything to es. Promotion data
    # will get updated during insert
    promo_channels = Channel.query.filter_by(public=True, deleted=False).join(
        ChannelPromotion, ChannelPromotion.channel == Channel.id).distinct()
    for channel in promo_channels:
        es_channel = api.ESChannel.updater(bulk=True)
        es_channel.set_document_id(channel.id)
        es_channel.add_field(channel.id, channel.promotion_map())
        es_channel.update()
    api.ESChannel.flush()


@manager.cron_command(interval=900)
@job_control
def update_user_promotions(date_from=None, date_to=None):
    """ Update promotion data for channels in ES """
    # Push everything to es. Promotion data
    # will get updated during insert
    promo_users = User.query.filter_by(is_active=True).join(
        UserPromotion, UserPromotion.user_id == User.id).distinct()
    for user in promo_users:
        es_user = api.ESUser.updater(bulk=True)
        es_user.set_document_id(user.id)
        es_user.add_field('promotion', user.promotion_map())
        es_user.update()
    api.ESUser.flush()


@manager.cron_command(interval=900)
@job_control
def process_video_instance_queue(date_from=None, date_to=None):
    """Create queued video instances."""
    from rockpack.mainsite.services.user.api import add_videos_to_channel
    records = VideoInstanceQueue.query.filter(
        VideoInstanceQueue.new_instance == None,
        VideoInstanceQueue.date_scheduled < date_to
    )
    for record in records:
        added = add_videos_to_channel(record.target_channel_rel, [record.source_instance],
                                      None, tag=record.tags)
        record.new_instance = added[0].id
        app.logger.info('Processed queue. Added %s to %s: %s',
                        record.source_instance, record.target_channel, record.new_instance)


@manager.cron_command(interval=86400)
@commit_on_success
def import_google_movies():
    freshold = datetime.now() - timedelta(days=app.config.get('GOOGLE_MOVIE_FRESHOLD', 120))
    year_format = re.compile(' \((20\d\d)\)')

    for channelid, location in app.config['GOOGLE_MOVIE_LOCATIONS']:
        start = 0
        video_ids = set()
        channel = Channel.query.get(channelid)
        existing = set(v for v, in VideoInstance.query.
                       filter_by(channel=channelid).join(Video).values('source_videoid'))
        while True:
            url = app.config['GOOGLE_MOVIE_URL'] % (location, start)
            html = get_external_resource(url).read()
            video_ids.update(re.findall('youtube.com/watch%3Fv%3D(.{11})', html))
            next = re.search('<a [^>]*start=(\d+)[^>]*><img[^>]*><br>Next</a>', html)
            if next:
                start = int(next.group(1))
                time.sleep(1)   # Don't get blocked by google
            else:
                break
        feed_ids = [('videos', id) for id in video_ids - existing]
        if feed_ids:
            playlist = batch_query(feed_ids, playlist='Googlemovietrailers/uploads')
            videos = []
            for video in playlist.videos:
                year_match = year_format.search(video.title)
                if video.date_published > freshold and (
                        not year_match or int(year_match.group(1)) >= freshold.year):
                    videos.append(video)
                else:
                    app.logger.debug('Skipped import of trailer "%s" (%s)',
                                     video.title, video.date_published)
            added = Video.add_videos(videos, 1)
            channel.add_videos(videos)
            app.logger.info('Added %d trailers to "%s"', added, channel.title)


@manager.cron_command(interval=900)
@job_control
def check_video_player_errors(date_from=None, date_to=None):
    """Scan player error records and check that videos are still available."""
    error_videos = set(v[0] for v in PlayerErrorReport.query.filter(
        PlayerErrorReport.date_updated.between(date_from, date_to)).
        join(VideoInstance, VideoInstance.id == PlayerErrorReport.video_instance).
        values('video'))
    if error_videos:
        video_qs = Video.query.filter(
            Video.source == 1, Video.visible == True, Video.id.in_(error_videos))
        get_youtube_video_data(video_qs, date_to)


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
                    app.logger.info('%s: marked not visible: noembed', id)
                    videos[id].visible = False
                #group = [e for e in entry.extension_elements if e.tag == 'group'][0]
                #print id, [(c.attributes, c.text) for c in group.children if c.tag == 'restriction']
            elif entry.batch_status.code == '404':
                app.logger.info('%s: marked not visible: %s', id, entry.batch_status.reason)
                if not videos[id].source_username:
                    videos[id].source_username = 'Unknown'
                videos[id].visible = False
            else:
                app.logger.warning('%s: %s', id, entry.batch_status.reason)
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


@manager.command
@commit_on_success
def set_original_channel_owner():
    instances = VideoInstance.query.\
        join(Channel, (Channel.id == VideoInstance.channel) & (Channel.deleted == False))
    dups = instances.with_entities(
        VideoInstance.video, func.count()
    ).group_by('1').having(func.count() > 1)
    for video, count in dups:
        candidates = instances.filter(VideoInstance.video == video)
        (original_instance, original_channel_owner), = candidates.\
            order_by(VideoInstance.date_added).\
            limit(1).values(VideoInstance.id, Channel.owner)
        candidates.filter(
            VideoInstance.id != original_instance,
            VideoInstance.original_channel_owner.is_(None)
        ).update({VideoInstance.original_channel_owner: original_channel_owner})
