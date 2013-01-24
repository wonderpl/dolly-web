# Environment configuration file
#
# All variables must be uppercase


DATABASE_URL = ''  # e.g. postgresql://foo:bar@localhost:5432/rockpack

AWS_ACCESS_KEY = ''
AWS_SECRET_KEY = ''
S3_BUCKET = ''
S3_THUMBNAIL_DIR = ''
SECRET_KEY = '22a20453891f41148e2251c4b2cef0df3426c4193914409cb0c5994b58fe77c5'

GOOGLE_CONSUMER_KEY = '902099289100.apps.googleusercontent.com'
GOOGLE_CONSUMER_SECRET = 'ja-jW0BDASKVIwIRFurpCaZi'

VIDEO_IMAGES = {'thumbnail_small': (249, 140,),
        'thumbnail_large': (137, 77,),
        'bar': (123, 69,)}

VIDEO_IMG_PATHS = {'original': 'images/videos/original/',
        'thumbnail_large': 'images/videos/thumbnail_large/',
        'thumbnail_small': 'images/videos/thumbnail_small/',
        'bar': 'images/videos/bar/'}

CHANNEL_IMAGES = {'thumbnail_large': (241, 171,),
        'thumbnail_small': (48, 34,),
        'carousel': (341,190,),
        'background': (1024, 705,)}

CHANNEL_IMG_PATHS = {'original': 'images/channel/original/',
        'thumbnail_large': 'images/channel/thumbnail_large/',
        'thumbnail_small': 'images/channel/thumbnail_small/',
        'carousel': 'images/channel/carousel/',
        'backgroud': 'images/channel/background/'}

AVATAR_IMAGES = {'avatar': (72, 72,)}
AVATAR_IMG_PATHS = {'original': 'images/avatar/original/'}
