from . import mappings


def add_owner_to_index(conn, owner):
    i = conn.index({
        'id': owner.id,
        'avatar_thumbnail': str(owner.avatar),
        'resource_url': owner.get_resource_url(False),
        'display_name': owner.display_name,
        'name': owner.username
        },
        mappings.USER_INDEX,
        mappings.USER_TYPE,
        id=owner.id)
    conn.indices.refresh(mappings.USER_INDEX)
    return i


def add_channel_to_index(conn, channel):
    i = conn.index({
        'id': channel['id'],
        'locale': channel['locale'],
        'subscribe_count': channel['subscribe_count'],
        'category': channel['category'],
        'description': channel['description'],
        'thumbnail_url': channel['thumbnail_url'],
        'cover_thumbnail_small_url': channel['cover_thumbnail_small_url'],
        'cover_thumbnail_large_url': channel['cover_thumbnail_large_url'],
        'cover_background_url': channel['cover_background_url'],
        'resource_url': channel['resource_url'],
        'title': channel['title'],
        'owner': channel['owner_id'],
        },
        mappings.CHANNEL_INDEX,
        mappings.CHANNEL_TYPE,
        id=channel['id'])
    conn.indices.refresh(mappings.CHANNEL_INDEX)
    return i


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
        mappings.VIDEO_INDEX,
        mappings.VIDEO,
        id=video_instance['id'])


def remove_channel_from_index(conn, channel_id):
    print conn.delete(mappings.CHANNEL_INDEX, mappings.CHANNEL_TYPE, channel_id)


def remove_video_from_index(conn, video_id):
    print conn.delete(mappings.VIDEO_INDEX, mappings.VIDEO_TYPE, video_id)
