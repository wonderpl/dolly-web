# Environment configuration file
#
# All variables must be uppercase


import pkg_resources
try:
    VERSION = pkg_resources.get_distribution('rockpack-mainsite').version
except pkg_resources.DistributionNotFound:
    VERSION = 'unknown'

FORCE_INDEX_INSERT_REFRESH = False  # used by elasticsearch

DATABASE_URL = ''  # e.g. postgresql://foo:bar@localhost:5432/rockpack

AWS_ACCESS_KEY = None
AWS_SECRET_KEY = None
S3_BUCKET = 'media.dev.rockpack.com'
IMAGE_CDN = 'http://media.dev.rockpack.com'

SECRET_KEY = '22a20453891f41148e2251c4b2cef0df3426c4193914409cb0c5994b58fe77c5'

# For admin OAuth login:
GOOGLE_CONSUMER_KEY = '902099289100.apps.googleusercontent.com'
GOOGLE_CONSUMER_SECRET = 'ja-jW0BDASKVIwIRFurpCaZi'

# For google API access:
GOOGLE_DEVELOPER_KEY = 'AIzaSyAIV4F5dpvDltQpE9CAWipWN57zuT_EIq4'

# For google analytics
GOOGLE_ANALYTICS_ACCOUNT = 'UA-39188851-2'

ELASTICSEARCH_URL = None

# Client ID for the iOS app
ROCKPACK_APP_CLIENT_ID = 'c8fe5f6rock873dpack19Q'

# Client ID for the javascript front-end
ROCKPACK_JS_CLIENT_ID = 'orockgqRScSlWKjsfVuxrQ'

CLIENT_IDS = ROCKPACK_APP_CLIENT_ID, ROCKPACK_JS_CLIENT_ID

IGNORE_ACCESS_TOKEN = False

# The "Mozilla Gecko" seems to be necessary for the gdata api to encode with gzip!
USER_AGENT = 'rockpack/%s (Mozilla Gecko)' % VERSION

# Default is first locale
ENABLED_LOCALES = ('en-us', 'en-gb')

# Base path on S3_BUCKET for images
IMAGE_BASE_PATH = 'images'

CHANNEL_IMAGES = dict(
    thumbnail_small=(44, 44),
    thumbnail_medium=(152, 152),
    thumbnail_large=(243, 243),
    background_portrait=(320, 568),
    background=(1024, 1024),
)

AVATAR_IMAGES = dict(
    thumbnail_small=(44, 44),
    thumbnail_medium=(60, 60),
    thumbnail_large=(120, 120),
)

ASSETS_MANIFEST = 'file'
ASSETS_CACHE = False
ASSETS_AUTO_BUILD = False

# Prefix for untitled channels
UNTITLED_CHANNEL = 'Untitled'

# Title, description, and cover image for default favourites channel
FAVOURITE_CHANNEL = 'Favorites', 'My favorite videos', 'fav2.jpg'

# Mapping from share object type to message (can have formatting)
SHARE_MESSAGE_MAP = dict(
    channel='Check out this channel on Rockpack',
    video_instance='Check out this video on Rockpack',
)

# Path to default avatar image used when creating users
DEFAULT_AVATAR = ''

DEFAULT_EMAIL_SOURCE = 'rockpack <noreply@rockpack.com>'

ENABLE_TIMINGS = True

# Toggle to enable test url
TEST_EXTERNAL_SYSTEM = False

# Credentials for "rockpack-dev" app on facebook
FACEBOOK_APP_ID = '131721883664256'
FACEBOOK_APP_SECRET = '9dc1d5cf8d5f9b96284303b3ab4d1d15'
FACEBOOK_APP_NAMESPACE = 'rockpack-dev'

# Credentials for "rockpack dev" app on twitter
TWITTER_CONSUMER_KEY = '0Pxmm1W7VdsxQFF1nsB9Jg'
TWITTER_CONSUMER_SECRET = 'y1EWKp7hDQdJWv1m1cL855Cja4jTJapP3cr39cOa4'
TWITTER_ACCESS_TOKEN_KEY = '1252401133-j2IilDJ9MIUr35kTJoxLas4YLWBxJbYxjMjSTnh'
TWITTER_ACCESS_TOKEN_SECRET = 'qmd88AaAfta2HOaBqyaLQOJHAK1jkeLugfsziBGMjk'
