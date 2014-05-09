# Environment configuration file
#
# All variables must be uppercase


import re
import pkg_resources
try:
    VERSION = pkg_resources.get_distribution('rockpack-mainsite').version
except pkg_resources.DistributionNotFound:
    VERSION = 'unknown'

FORCE_INDEX_INSERT_REFRESH = False  # used by elasticsearch

DATABASE_URL = ''  # e.g. postgresql://foo:bar@localhost:5432/rockpack
SLAVE_DATABASE_URL = ''

CACHE_TYPE = 'simple'

AWS_ACCESS_KEY = None
AWS_SECRET_KEY = None
S3_BUCKET = 'media.dev.rockpack.com'
IMAGE_CDN = 'http://media.dev.rockpack.com'

VIDEO_S3_BUCKET = 'video.dev.rockpack.com'

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
PHG_AFFILIATE_TOKEN = '11ls25'
ITUNES_APP_ID = '660697542'
ITUNES_APP_LINK = 'https://itunes.apple.com/app/rockpack/id%s?mt=8&ls=1&at=%s' % (ITUNES_APP_ID, PHG_AFFILIATE_TOKEN)

HELP_SITE_LINK = 'http://help.rockpack.com/'

# For iOS app deeplinking
IOS_APP_URL_SCHEME = 'rockpack'

ELASTICSEARCH_URL = None

MYRRIX_URL = None

# Client ID for the iOS app
ROCKPACK_APP_CLIENT_ID = 'c8fe5f6rock873dpack19Q'

# Client ID for the javascript front-end
ROCKPACK_JS_CLIENT_ID = 'orockgqRScSlWKjsfVuxrQ'

CLIENT_IDS = ROCKPACK_APP_CLIENT_ID, ROCKPACK_JS_CLIENT_ID

IGNORE_ACCESS_TOKEN = False

OOYALA_PLAYER_ID = '8e49f5aacf724f33b534cadfc4485e6b'
OOYALA_API_KEY = 'YzYW8xOshpVwePawyVliU0L_tBj_.yPTX2'
OOYALA_SECRET = 'xxx'

ROMEO_ACCOUNT_VERIFY_URL = 'https://romeo.wonderpl.com/_verify_account'
ROMEO_WS_URL = 'https://romeo.wonderpl.com/api'

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

PROFILE_IMAGES = dict(
    thumbnail_medium=(320, 338),
    ipad_highlight=(616, 240),
    ipad=(927, 512),
)

BRAND_PROFILE_IMAGES = PROFILE_IMAGES

ASSETS_URL = '/static'
ASSETS_MANIFEST = 'file'
ASSETS_CACHE = False
ASSETS_AUTO_BUILD = False

EMAIL_TEMPLATE_PATH = 'static/assets/emails'

# Prefix for untitled channels
UNTITLED_CHANNEL = 'Untitled'

# Title, description, and cover image for default favourites channel
FAVOURITE_CHANNEL = 'Favorites', 'My favorite videos', 'fav2.jpg'

# Toggle to enable user categorisation conditions on and off
ENABLE_USER_CATEGORISATION_CONDITIONS = False

USER_CATEGORISATION_VIDEO_THRESHOLD = 10

# Mapping from share object type to message (can have formatting)
SHARE_MESSAGE_MAP = dict(
    video_instance=dict(
        message=u"I found \"{0[title]}\" on @Rockpack and thought you might like it too.",
        message_email=u"I found \"{0[title]}\" on Rockpack and thought you might like it too.",
        message_twitter=u"Look what I found on @Rockpack",
        message_facebook=u"Look what I found on Rockpack",
    ),
    channel=dict(
        message=u"I think you're going to love the video pack \"{0[title]}\" on @Rockpack.",
        message_email=u"I think you're going to love the video pack \"{0[title]}\" on Rockpack.",
        message_twitter=u"I found this great pack of videos on @Rockpack",
        message_facebook=u"I found this great pack of videos on Rockpack",
    ),
)

PUSH_NOTIFICATION_MAP = dict(
    subscribed=('channel', "%@ has subscribed to your channel"),
    joined=('user', "Your Facebook friend %@ has joined Rockpack"),
    repack=('video', "%@ has re-packed one of your videos"),
    #unavailable=('video', "One of your videos is no longer available"),
    comment_mention=('video', "%@ has mentioned you in a comment"),
    starred=('video', "%@ has liked your video"),
)

# Keep as True until app is updated to use /ws/complete/all/ instead.
USE_ALL_TERMS_FOR_VIDEO_COMPLETE = True

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

FEEDBACK_RECIPIENT = 'feedback@rockpack.com'

REACTIVATION_EMAIL_TRACKING_PARAMS = dict(utm_medium='email', utm_campaign='react')
REACTIVATION_THRESHOLD_DAYS = 7

SQS_REGION = 'eu-west-1'
SQS_CRON_QUEUE = 'mainsite-cron'
SQS_EMAIL_QUEUE = 'mainsite-email'
SQS_BACKGROUND_QUEUE = None
SQS_ELASTICSEARCH_QUEUE = None

ENABLE_TIMINGS = True

# Toggle to enable test url
TEST_EXTERNAL_SYSTEM = False

# Settings for Google Movie trailer service
GOOGLE_MOVIE_URL = 'http://www.google.com/movies?near=%s&start=%d'
GOOGLE_MOVIE_LOCATIONS = ('chfSOUZ6eqrIbC3KaKmnThxg', 'london'), ('chRMmzwR-FXdALSPHnkx9tkQ', 'new york')

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

SHARE_REDIRECT_PASSTHROUGH_PARAMS = 'utm_source', 'utm_medium', 'utm_campaign', 'video'

# From http://detectmobilebrowsers.com/about
MOBILE_BROWSER_RE1 = re.compile(r"(android|bb\\d+|meego).+mobile|avantgo|bada\\/|blackberry|blazer|compal|elaine|fennec|hiptop|iemobile|ip(hone|od)|iris|kindle|lge |maemo|midp|mmp|mobile.+firefox|netfront|opera m(ob|in)i|palm( os)?|phone|p(ixi|re)\\/|plucker|pocket|psp|series(4|6)0|symbian|treo|up\\.(browser|link)|vodafone|wap|windows (ce|phone)|xda|xiino", re.I | re.M)
MOBILE_BROWSER_RE2 = re.compile(r"1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\\-(n|u)|c55\\/|capi|ccwa|cdm\\-|cell|chtm|cldc|cmd\\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\\-s|devi|dica|dmob|do(c|p)o|ds(12|\\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\\-|_)|g1 u|g560|gene|gf\\-5|g\\-mo|go(\\.w|od)|gr(ad|un)|haie|hcit|hd\\-(m|p|t)|hei\\-|hi(pt|ta)|hp( i|ip)|hs\\-c|ht(c(\\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\\-(20|go|ma)|i230|iac( |\\-|\\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\\/)|klon|kpt |kwc\\-|kyo(c|k)|le(no|xi)|lg( g|\\/(k|l|u)|50|54|\\-[a-w])|libw|lynx|m1\\-w|m3ga|m50\\/|ma(te|ui|xo)|mc(01|21|ca)|m\\-cr|me(rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\\-2|po(ck|rt|se)|prox|psio|pt\\-g|qa\\-a|qc(07|12|21|32|60|\\-[2-7]|i\\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\\-|oo|p\\-)|sdk\\/|se(c(\\-|0|1)|47|mc|nd|ri)|sgh\\-|shar|sie(\\-|m)|sk\\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\\-|v\\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\\-|tdg\\-|tel(i|m)|tim\\-|t\\-mo|to(pl|sh)|ts(70|m\\-|m3|m5)|tx\\-9|up(\\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|yas\\-|your|zeto|zte\\-", re.I | re.M)
