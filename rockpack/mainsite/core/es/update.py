from rockpack.mainsite import app
from rockpack.mainsite.services.video import models
from rockpack.mainsite.core.dbapi import db, commit_on_success
from . import api


@commit_on_success
def update_most_influential_video(video_ids=None):
    query = models.get_influential_instances(video_ids=video_ids)

    instance_counts = {}
    influential_index = {}
    favs = []

    for _id, video, fav, source_channel, count in query.yield_per(6000):
        # Set the count for the video instance
        instance_counts[(_id, video)] = count
        if fav:
            favs.append(_id)
        # If the count is higher for the same video than
        # the previous instance, mark this instance as the
        # influential one for the video
        i_id, i_count = influential_index.setdefault(video, (_id, count))

        # Count will always be at least 1
        # but should really be zero if no children
        if not source_channel and count == 1:
            count = 0

        if (count > i_count) or\
                (count == i_count) and not source_channel:
            # If we've already got a video with the same count ...
            if (count == i_count):
                # ... and if what we want to set as most influential
                # is a fav, and the existing one isn't a fav ...
                if fav and i_id not in favs:
                    # ... ignore this one because we'd prefer non favs
                    # as the most influential video
                    continue

            influential_index.update({video: (_id, count,)})

    for (_id, video), count in instance_counts.iteritems():
        models.VideoInstance.query.filter(
            models.VideoInstance.id == _id
        ).update(
            {models.VideoInstance.most_influential: True if influential_index.get(video, '')[0] == _id else False}
        )


def _video_terms_channel_mapping(channel_ids):
    """ Get all the video terms for a channel """
    video_details = db.session.query(models.VideoInstance.channel, models.Video.title).join(
        models.Video,
        (models.VideoInstance.video == models.Video.id) &
        (models.Video.visible == True)
    ).filter(models.VideoInstance.channel.in_(channel_ids))

    channel_map = {}

    for (channel_id, video_title) in video_details:
        channel_map.setdefault(channel_id, []).append(video_title)

    return channel_map


def _category_channel_mapping(channel_ids):
    """ Get the categories belonging to videos
        on a channel """
    # Reset channel catgegory
    query = models.VideoInstance.query.filter(
        models.VideoInstance.channel.in_(channel_ids)
    ).with_entities(
        models.VideoInstance.category,
        models.VideoInstance.channel
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
    return qcat


def update_potential_categories(channelid, category_map):
    if app.config.get('DOLLY', False):
        potential_cats = category_map.get(channelid, None)
        if potential_cats:
            new_cat = update_average_channel_category(channelid, potential_cats)
            return new_cat


def update_video_related_channel_meta(channel_ids):
    channel_map = _video_terms_channel_mapping(channel_ids)
    print 'channel_ids'
    category_map = _category_channel_mapping(channel_ids)

    try:
        for channel_id in set(category_map.keys() + channel_map.keys()):
            ec = api.ESChannel.updater(bulk=True)
            ec.set_document_id(channel_id)
            video_titles = channel_map.get(channel_id, None)
            if video_titles:
                ec.add_field('video_terms', video_titles)
                ec.add_field('video_count', len(video_titles))

            # NOTE: dolly only
            if app.config.get('DOLLY', False):
                new_cat = update_potential_categories(channel_id, category_map)
                if new_cat:
                    ec.add_field('category', new_cat)

            # Update the es record
            ec.update()
    except Exception as e:
        db.session.rollback()
        raise e
    else:
        db.session.commit()

    # NOTE: dolly only
    if app.config.get('DOLLY', False):
        api.update_user_categories(
            list(
                set([_[0] for _ in models.Channel.query.filter(
                    models.Channel.id.in_(channel_ids)).values('owner')])))

    # Final flush to clear bulk queued updates
    api.ESChannel.flush()
