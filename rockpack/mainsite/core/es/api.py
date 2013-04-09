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


def add_video_to_index(conn, video_instance):
    return conn.index({
        'id': video_instance['id'],
        'locale': video_instance['locale'],
        'channel': video_instance['channel'],
        'category': video_instance['category'],
        'title': video_instance['title'],
        'date_added': video_instance['date_added'].isoformat(),
        'position': video_instance['position'],
        'video': {
            'id': video_instance['video_id'],
            'thumbnail_url': video_instance['thumbnail_url'],
            'source': video_instance['source'],
            'source_id': video_instance['source_id'],
            'duration': video_instance['duration'],
            }
        },
        mappings.VIDEO_INDEX,
        mappings.VIDEO_TYPE,
        id=video_instance['id'])


def remove_channel_from_index(conn, channel_id):
    print conn.delete(mappings.CHANNEL_INDEX, mappings.CHANNEL_TYPE, channel_id)


def remove_video_from_index(conn, video_id):
    print conn.delete(mappings.VIDEO_INDEX, mappings.VIDEO_TYPE, video_id)
