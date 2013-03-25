def add_channel_to_index(conn, channel, owner_id, locale):
    from rockpack.mainsite.services.video.models import Category
    cat_map = {c[0]:c[1] for c in Category.query.filter(Category.parent!=None).values('id', 'parent')}
    return conn.index({
        'id': channel['id'],
        'subscribe_count': channel['subscribe_count'],
        'category': [
            channel['category'],
            cat_map[channel['category']]
            ],
        'description': channel['description'],
        'thumbnail_url': channel['thumbnail_url'],
        'cover_thumbnail_small_url': channel['cover_thumbnail_small_url'],
        'cover_thumbnail_large_url': channel['cover_thumbnail_large_url'],
        'cover_background_url': channel['cover_background_url'],
        'resource_url': channel['resource_url'],
        'title': channel['title'],
        'owner': owner_id,
        },
        locale,
        'channels',
        id=channel['id'])


def add_video_to_index(conn, video_instance, video, locale):
    return conn.index({
        'id': video_instance['id'],
        'channel': video_instance['channel'],
        'category': video_instance['category'],
        'title': video_instance['title'],
        'video': {
            'id': video['id'],
            'thumbnail_url': video['thumbnail_url'],
            'view_count': video_instance['view_count']
            }
        },
        locale,
        'videos',
        id=video_instance['id'])


def remove_channel_from_index(conn, channel_id, locale):
    conn.delete(locale, 'channels', channel_id)


def remove_video_from_index(conn, video_id, locale):
    conn.delete(locale, 'videos', video_id)
