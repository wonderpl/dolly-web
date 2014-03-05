from sqlalchemy import func
from sqlalchemy.orm import aliased
from rockpack.mainsite import app
from rockpack.mainsite.services.video import models
from rockpack.mainsite.core.dbapi import db
from . import api


def _update_most_influential_video(video_ids):
    # Re-calculate most influential
    if not video_ids:
        return

    child = aliased(models.VideoInstance, name='child')
    query = db.session.query(
        models.VideoInstance.id,
        models.VideoInstance.video,
        child.source_channel,
        func.count(models.VideoInstance.id)
    ).outerjoin(
        child,
        (models.VideoInstance.video == child.video) &
        (models.VideoInstance.channel == child.source_channel)
    ).filter(
        models.VideoInstance.video.in_(video_ids)
    ).group_by(models.VideoInstance.id, models.VideoInstance.video, child.source_channel)

    instance_counts = {}
    influential_index = {}

    for _id, video, source_channel, count in query.yield_per(6000):
        # Set the count for the video instance
        instance_counts[(_id, video)] = count
        # If the count is higher for the same video than
        # the previous instance, mark this instance as the
        # influential one for the video
        i_id, i_count = influential_index.get(video, [None, 0])

        # Count will always be at least 1
        # but should really be zero if no children
        if not source_channel and count == 1:
            count = 0
        if (count > i_count) or\
                (count == i_count) and not source_channel:
            influential_index.update({video: (_id, count,)})

    for (_id, video), count in instance_counts.iteritems():
        ev = api.ESVideo.updater(bulk=True)
        ev.set_document_id(_id)
        ev.add_field('child_instance_count', count)
        ev.add_field('most_influential', True if influential_index.get(video, '')[0] == _id else False)
        ev.update()
    api.ESVideo.flush()


def _video_terms_channel_mapping(channel_ids):
    """ Get all the video terms for a channel """
    video_details = db.session.query(models.VideoInstance.channel, models.Video.title).join(
        models.Video,
        models.VideoInstance.video == models.Video.id
    ).filter(models.VideoInstance.channel.in_(channel_ids))

    channel_map = {}

    for (channel_id, video_title) in video_details:
        channel_map.setdefault(channel_id, []).append(video_title)

    return channel_map


def _category_channel_mapping(channel_ids):
    """ Get the categories belonging to videos
        on a channel """
    # Reset channel catgegory
    query = db.session.query(
        models.VideoInstance.category, models.VideoInstance.channel
    ).filter(
        models.VideoInstance.channel.in_(channel_ids)
    ).order_by(models.VideoInstance.channel)

    category_map = {}

    for instance_cat, channel_id in query:
        channel_cat_counts = category_map.setdefault(channel_id, {})
        current_count = channel_cat_counts.setdefault(instance_cat, 0)
        channel_cat_counts[instance_cat] = current_count + 1

    return category_map


def update_average_channel_category(channelid, cat_count_map):
    try:
        cat = next(cat for cat, count in cat_count_map.items() if count >= sum(cat_count_map.values()) * 0.6)
    except StopIteration:
        cat = []

    # Update the database
    qcat = cat or None
    c = models.Channel.query.get(channelid)
    if qcat != c.category:
        c.category = qcat
        c.save()
    return qcat


def _update_video_related_channel_meta(channel_ids):
    channel_map = _video_terms_channel_mapping(channel_ids)
    category_map = _category_channel_mapping(channel_ids)

    for channel_id in set(category_map.keys() + channel_map.keys()):
        ec = api.ESChannel.updater(bulk=True)
        ec.set_document_id(channel_id)
        video_titles = channel_map.get(channel_id, None)
        if video_titles:
            ec.add_field('video_terms', video_titles)
            ec.add_field('video_count', len(video_titles))

        # NOTE: dolly only
        if app.config.get('DOLLY', False):
            potential_cats = category_map.get(channel_id, None)
            if potential_cats:
                new_cat = update_average_channel_category(channel_id, potential_cats)
                # Set es field
                ec.add_field('category', new_cat)

        # Update the es record
        ec.update()

    # NOTE: dolly only
    if app.config.get('DOLLY', False):
        api.update_user_categories(
            list(
                set([_[0] for _ in models.Channel.query.filter(
                    models.Channel.id.in_(channel_ids)).values('owner')])))

    # Final flush to clear bulk queued updates
    api.ESChannel.flush()
