def add_channel_to_index(conn, channel, owner_id, locale):
    from rockpack.mainsite.services.video.models import Category
    cat_map = {c[0]:c[1] for c in Category.query.filter(Category.parent!=None).values('id', 'parent')}
    return conn.index({
        'id': channel['id'],
        'locale': locale,
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
        'channel',
        'channels',
        id=channel['id'])


def add_video_to_index(conn, video_instance, video, locale):
    return conn.index({
        'id': video_instance['id'],
        'locale': locale,
        'channel': video_instance['channel'],
        'category': video_instance['category'],
        'title': video_instance['title'],
        'date_added': video_instance['date_added'],
        'position': video_instance['position'],
        'video': {
            'id': video['id'],
            'thumbnail_url': video['thumbnail_url'],
            'view_count': video['view_count'],
            'star_count': video['star_count'],
            'source': video['source'],
            'source_id': video['source_id'],
            'duration': video['duration'],
            }
        },
        'videos',
        'video',
        id=video_instance['id'])


def remove_channel_from_index(conn, channel_id):
    conn.delete('channels', 'channel', channel_id)


def remove_video_from_index(conn, video_id):
    conn.delete('videos', 'video', video_id)
