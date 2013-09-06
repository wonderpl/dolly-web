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
SLAVE_DATABASE_URL = ''

AWS_ACCESS_KEY = None
AWS_SECRET_KEY = None
S3_BUCKET = 'media.dev.rockpack.com'
IMAGE_CDN = 'http://media.dev.rockpack.com'

#SHARE_SUBDOMAIN = 'share'  # for share urls

SECRET_KEY = '22a20453891f41148e2251c4b2cef0df3426c4193914409cb0c5994b58fe77c5'

# For admin OAuth login:
GOOGLE_CONSUMER_KEY = '902099289100.apps.googleusercontent.com'
GOOGLE_CONSUMER_SECRET = 'ja-jW0BDASKVIwIRFurpCaZi'

# For google API access:
GOOGLE_DEVELOPER_KEY = 'AIzaSyAIV4F5dpvDltQpE9CAWipWN57zuT_EIq4'

# For google analytics
GOOGLE_ANALYTICS_ACCOUNT = 'UA-39188851-2'

# For app store links
ITUNES_APP_ID = '660697542'

# For iOS app deeplinking
ROCKPACK_IOS_URL_SCHEME = 'rockpack'

INTERSTITIAL_ITUNES_LINK = True

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
    message=u"Check out this great {0[object_type]} on @rockpack",
    message_email=u"Check out this great {0[object_type]} \"{0[title]}\" on Rockpack",
    message_twitter=u"Check out this great {0[object_type]} on @rockpack",
    message_facebook=u"Check out this great {0[object_type]} on Rockpack",
)

RECOMMENDER_CATEGORY_BOOSTS = dict(
    gender={
        'm': (
            (138, 1.4),   # gaming/playstation
            (205, 1.4),   # living/cars-bikes
            (147, 1.4),   # gaming/walkthroughs
            (378, 1.4),   # sport/football
            (368, 1.3),   # gaming/nintendo
            (369, 1.3),   # gaming/mobile
            (196, 1.3),   # style/men
            (213, 1.3),   # knowledge/tech
            (139, 1.3),   # gaming/xbox
            (379, 1.3),   # sport/Basketball
            (375, 1.2),   # sport/extreme
            (240, 0.4),   # food/baking
            (167, 0.3),   # tv-news/reality
            (199, 0.1),   # style/beauty
            (464, 0.1),   # style/hair
        ),
        'f': (
            (199, 2.6),   # style/beauty
            (464, 2.5),   # style/hair
            (240, 2.1),   # food/baking
            (123, 1.9),   # music/pop
            (374, 1.9),   # style/fashion
            (208, 1.7),   # living/health
            (468, 1.6),   # comedy/animals
            (444, 1.6),   # living/pets
            (167, 1.6),   # tv-news/reality
            (238, 1.5),   # food/healthy
            (459, 0.2),   # sport/All Sports
            (378, 0.2),   # sport/football
            (460, 0.1),   # sport/mma
            (379, 0.1),   # sport/Basketball
            (196, 0.1),   # style/men
        ),
    },
    age={
        13: (
            (448, 2.0),   # FILM/Family
        ),
        18: (
            (179, 2.6),   # comedy/vlogs
            (123, 1.7),   # music/pop
            (167, 1.6),   # tv-news/reality
            (366, 1.6),   # gaming/gamers
            (208, 0.3),   # living/health
            (236, 0.2),   # food/chefs
            (437, 0.2),   # knowledge/business
        ),
        25: (
            (179, 1.5),   # comedy/vlogs
            (366, 1.4),   # gaming/gamers
            (126, 1.4),   # music/electronic
            (147, 1.4),   # gaming/walkthroughs
            (128, 1.3),   # music/hip-hop
        ),
        35: (
            (441, 1.7),   # knowledge/how-to
            (236, 1.6),   # food/chefs
            (181, 1.5),   # comedy/stand-up
            (237, 1.4),   # food/recipes
            (138, 1.4),   # gaming/playstation
            (436, 1.4),   # knowledge/education
            (217, 1.4),   # knowledge/talks
            (213, 1.4),   # knowledge/tech
            (437, 1.3),   # knowledge/business
            (179, 0.5),   # comedy/vlogs
        ),
        45: (
            (452, 1.7),   # music/country
            (221, 1.7),   # knowledge/other
            (124, 1.5),   # music/rock
            (444, 1.4),   # living/pets
            (209, 1.4),   # living/travel
            (205, 1.4),   # living/cars-bikes
            (165, 1.3),   # tv-news/series
            (214, 1.3),   # knowledge/history
            (126, 0.5),   # music/electronic
            (147, 0.5),   # gaming/walkthroughs
            (366, 0.4),   # gaming/gamers
            (179, 0.2),   # comedy/vlogs
        ),
        55: (
            (214, 2.6),   # knowledge/history
            (221, 2.6),   # knowledge/other
            (155, 2.1),   # FILM/Movie extras
            (444, 2.1),   # living/pets
            (156, 2.0),   # FILM/shorts
            (165, 2.0),   # tv-news/series
            (209, 1.9),   # living/travel
            (468, 1.9),   # comedy/animals
            (237, 1.8),   # food/recipes
            (238, 1.8),   # food/healthy
            (126, 0.4),   # music/electronic
            (368, 0.4),   # gaming/nintendo
            (128, 0.3),   # music/hip-hop
            (147, 0.3),   # gaming/walkthroughs
            (179, 0.2),   # comedy/vlogs
            (366, 0.2),   # gaming/gamers
        ),
    },
)

# Path to default avatar image used when creating users
DEFAULT_AVATAR = ''

DEFAULT_EMAIL_SOURCE = 'rockpack <noreply@rockpack.com>'

SQS_REGION = 'eu-west-1'
SQS_CRON_QUEUE = 'mainsite-cron'
SQS_EMAIL_QUEUE = 'mainsite-email'

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

# APNS settings
APNS_PUSH_TYPE = 'push_sandbox'
APNS_FEEDBACK_TYPE = 'feedback_sandbox'
APNS_CERT_NAME = 'apns-dev.pem'
APNS_PASSPHRASE = 'rockpack'

SHARE_REDIRECT_PASSTHROUGH_PARAMS = 'utm_source', 'utm_medium', 'utm_campaign'
