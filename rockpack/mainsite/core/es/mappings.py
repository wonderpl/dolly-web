from rockpack.mainsite import app

app_prefix = 'dolly' if app.config.get('DOLLY', False) else 'rockpack'

CHANNEL_TYPE = 'channel'
VIDEO_TYPE = 'video'
USER_TYPE = 'user'

CHANNEL_ALIAS = CHANNEL_INDEX = app_prefix + '_channel'
VIDEO_ALIAS = VIDEO_INDEX = app_prefix + '_video'
USER_ALIAS = USER_INDEX = app_prefix + '_user'

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

if app.config.get('DOLLY', False):
    video_mapping = {
        "properties": {
            "id": {"type": "string"},
            "date_added": {"type": "date"},
            "title": {
                "type": "string",
                "analyzer": "snowball"
            },
            "position": {"type": "integer"},
            "category": {
                "type": "integer"},
            "locales": locale_count_dict,
            "channel": {
                "type": "string",
                "index": "not_analyzed"
            },
            "channel_title": {
                "type": "string",
                "analyzer": "snowball"
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
                    "source_username": {"type": "string"},
                    "date_published": {"type": "date"},
                    "duration": {"type": "integer"}
                }
            },
            "recent_user_likes": {
                "type": "string",
                "index": "not_analyzed"
            },
            "country_restriction": {
                "properties": {
                    "allow": {
                        "type": "string",
                        "index": "not_analyzed",
                        "null_value": []
                    },
                    "deny": {
                        "type": "string",
                        "index": "not_analyzed",
                        "null_value": []
                    }
                }
            },
            "child_instance_count": {
                "type": "integer"
            },
            "owner": {
                "properties": {
                    "avatar": {
                        "type": "string",
                        "index": "not_analyzed"
                    },
                    "display_name": {
                        "type": "string",
                        "index": "not_analyzed"
                    },
                    "resource_url": {
                        "type": "string",
                        "index": "not_analyzed"
                    }
                }
            },
            "most_influential": {
                "type": "boolean",
                "null_value": False
            },
            "comments": {
                "properties": {
                    "count": {
                        "type": "integer",
                        "null_value": 0
                    }
                }
            },
            "tags": {
                "type": "string",
                "index": "not_analyzed",
                "null_value": []
            }
        }
    }
else:
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
            "channel_title": {
                "type": "string",
                "analyzer": "snowball"
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
                    "source_username": {"type": "string"},
                    "date_published": {"type": "date"},
                    "duration": {"type": "integer"}
                }
            },
            "recent_user_likes": {
                "type": "string",
                "index": "not_analyzed"
            },
            "country_restriction": {
                "properties": {
                    "allow": {
                        "type": "string",
                        "index": "not_analyzed",
                        "null_value": []
                    },
                    "deny": {
                        "type": "string",
                        "index": "not_analyzed",
                        "null_value": []
                    }
                }
            },
            "child_instance_count": {
                "type": "integer"
            },
            "owner": {
                "properties": {
                    "avatar": {
                        "type": "string",
                        "index": "not_analyzed"
                    },
                    "display_name": {
                        "type": "string",
                        "index": "not_analyzed"
                    },
                    "resource_url": {
                        "type": "string",
                        "index": "not_analyzed"
                    }
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
        "display_name": {
            "type": "string"},
        "username": {
            "type": "string"},
        "id": {
            "type": "string",
            "index": "not_analyzed"
        },
        "profile_cover_url": {
            "type": "string",
            "index": "not_analyzed"
        },
        "description": {
            "type": "string",
            "index": "not_analyzed"
        },
        "site_url": {
            "type": "string",
            "index": "not_analyzed"
        },
        "brand": {
            "type": "boolean",
            "null_value": False,
        },
        "subscriber_count": {
            "type": "integer",
            "null_value": 0
        },
        "category": {
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
        "date_updated": {"type": "date"},
        "date_published": {"type": "date"},
        "video_frequency": {"type": "integer"},
        "video_last_added": {"type": "date"},
        "update_frequency": {"type": "float", "null_value": 0.0},
        "subscriber_frequency": {"type": "float", "null_value": 0.0},
        "editorial_boost": {"type": "float", "null_value": 1.0},
        "favourite": {"type": "boolean"},
        "verified": {"type": "boolean"},
        "video_terms": {
            "type": "string",
            "analyzer": "snowball"
        },
        "video_count": {
            "type": "integer",
            "null_value": 0
        },
        "keywords": {
            "type": "string",
            "index": "not_analyzed"
        },
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
            "analyzer": "snowball"
        },
        "cover": {
            "properties": {
                "thumbnail_url": {
                    "type": "string",
                    "index": "not_analyzed"
                },
                "aoi": {
                    "type": "float",
                }
            },
        },
        "thumbnail_url": {
            "type": "string",
            "index": "not_analyzed"},
        "resource_url": {
            "type": "string",
            "index": "not_analyzed"},
        "owner": {
            "type": "string",
            "index": "not_analyzed"},
        "promotion": {
            "type": "string",
            "index": "not_analyzed"
        },
        "normalised_rank": {
            "properties": {
                "en-us": {
                    "type": "float",
                    "null_value": 0.0
                },
                "en-gb": {
                    "type": "float",
                    "null_value": 0.0
                }
            }
        }
    }
}
