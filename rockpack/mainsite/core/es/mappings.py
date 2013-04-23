CHANNEL_INDEX = 'channels'
VIDEO_INDEX = 'videos'
USER_INDEX = 'users'


CHANNEL_TYPE = 'channel'
VIDEO_TYPE = 'video'
USER_TYPE = 'user'

locale_count_dict = {
    "properties": {
        "en-gb": {
            "properties": {
                "view_count": {
                    "type": "integer"
                },
                "star_count": {
                    "type": "integer"
                }
            }
        },
        "en-us": {
            "properties": {
                "view_count": {
                    "type": "integer"
                },
                "star_count": {
                    "type": "integer"
                }
            }
        }
    }
}

video_mapping = {
    "properties": {
        "id": {"type": "string"},
        "date_added": {"type": "date"},
        "title": {
            "type": "string",
            "index": "analyzed"
        },
        "position": {"type": "integer"},
        "category": {
            "type": "integer"},
        "locales": locale_count_dict,
        "channel": {
            "type": "string",
            "index": "not_analyzed"
        },
        "video": {
            "properties": {
                "id": {
                    "type": "string",
                    "index": "not_analyzed"},
                "thumbnail_url": {
                    "type": "string",
                    "index": "not_analyzed"},
                "view_count": {"type": "integer"},
                "star_count": {"type": "integer"},
                "source": {
                    "type": "string",
                    "index": "not_analyzed"},
                "source_id": {"type": "string"},
                "duration": {"type": "integer"}
            }
        }
    }
}


user_mapping = {
    "properties": {
        "avatar_thumbnail_url": {
            "type": "string",
            "index": "not_analyzed"},
        "resource_url": {
            "type": "string",
            "index": "not_analyzed"},
        "display_name": {"type": "string"},
        "name": {"type": "string"},
        "id": {
            "type": "string",
            "index": "not_analyzed"
        }
    }
}


channel_mapping = {
    "properties": {
        "id": {
            "type": "string",
            "index": "not_analyzed"},
        "locales": locale_count_dict,
        "date_added": {"type": "date"},
        "ecommerce_url": {
            "type": "string",
            "index": "not_analyzed"
        },
        "category": {
            "type": "integer",
        },
        "subscriber_count": {"type": "integer"},
        "public": {"type": "boolean"},
        "description": {
            "type": "string",
            "index": "analyzed"
        },
        "title": {
            "type": "string",
            "index": "analyzed"
        },
        "thumbnail_url": {
            "type": "string",
            "index": "not_analyzed"},
        "cover_thumbnail_small_url": {
            "type": "string",
            "index": "not_analyzed"},
        "cover_thumbnail_large_url": {
            "type": "string",
            "index": "not_analyzed"},
        "cover_background_url": {
            "type": "string",
            "index": "not_analyzed"},
        "resource_url": {
            "type": "string",
            "index": "not_analyzed"},
        "owner": {
            "type": "string",
            "index": "not_analyzed"}
    }
}
