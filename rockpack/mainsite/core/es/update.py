from sqlalchemy import func
from sqlalchemy.orm import aliased
from rockpack.mainsite.services.video import models
from rockpack.mainsite.core.dbapi import readonly_session
from . import api


def _update_most_influential_video(video_ids):
    # Re-calculate most influential
    child = aliased(models.VideoInstance, name='child')
    query = readonly_session.query(
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
        # If the count is higher for the same video that
        # the previous instance, mark this instance as the
        # influential one for this video
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


def _video_terms_channel_mapping(channel_ids, channel_map={}):
    """ Get all the video terms for a channel """
    video_details = readonly_session.query(models.VideoInstance.channel, models.Video.title).join(
        models.Video,
        models.VideoInstance.video == models.Video.id
    ).filter(models.VideoInstance.channel.in_(channel_ids))
    for (channel_id, video_title) in video_details:
        channel_map.setdefault(channel_id, []).append(video_title)


def _category_channel_mapping(channel_ids, category_map={}):
    """ Get the categories belonging to videos
        on a channel """
    # Reset channel catgegory
    query = readonly_session.query(
        models.VideoInstance.category, models.VideoInstance.channel
    ).filter(
        models.VideoInstance.channel.in_(channel_ids)
    ).order_by(models.VideoInstance.channel)

    category_map = {}
    for instance_cat, channel_id in query:
        channel_cat_counts = category_map.setdefault(channel_id, {})
        current_count = channel_cat_counts.setdefault(instance_cat, 0)
        channel_cat_counts[instance_cat] = current_count + 1


def _update_video_related_channel_meta(channel_ids):
    channel_map = {}
    category_map = {}

    _video_terms_channel_mapping(channel_ids, channel_map=channel_map)
    _category_channel_mapping(channel_ids, category_map=category_map)

    for channel_id in set(category_map.keys() + channel_map.keys()):
        ec = api.ESChannel.updater(bulk=True)
        ec.set_document_id(channel_id)
        video_titles = channel_map.get(channel_id, None)
        if video_titles:
            ec.add_field('video_terms', video_titles)
            ec.add_field('video_count', len(video_titles))
        potential_cats = category_map.get(channel_id, None)
        if potential_cats:
            cat = next(cat for cat, count in potential_cats.items() if count >= sum(potential_cats.values()) * 0.6)
            if cat:
                ec.add_field('category', cat)
        ec.update()
    api.ESChannel.flush()
