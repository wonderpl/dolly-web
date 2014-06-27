# load _decrypt function from ROCKPACK_SETTINGS file
import os
execfile(os.environ['ROCKPACK_SETTINGS'])

DOLLY = True

SECRET_KEY = _decrypt(':~l2\xc7\xc5\xe38\x91\xc5\x9fcu\xf7\x15\xe8\x1d\x11\xe7!\x94\xdf\xca6\x07\xeb1\n\x14\xa2\x01<\x82\x90\xcd\x8c\xa6\x97\x92n{\x12}\x01>\xa7O\x997\xa7\xb3\xd8\xdbE\xa4\xa2G3\xeczw~"\xe8')

DB_PASSWORD = _decrypt('o\xa9\xe7\xc5\x08\x03L3')
DATABASE_URL = 'postgresql://mainsite:%s@db1/dolly' % DB_PASSWORD
#SLAVE_DATABASE_URL = None

GOOGLE_CONSUMER_KEY = '981375550038-dbckr7s2hb5rsaohj9j4fhl0cbu4col7.apps.googleusercontent.com'
GOOGLE_CONSUMER_SECRET = _decrypt('d3So=\x9e\xa7\x02\x97\xd5`\x1a\xae\x8f\xc5\xd1\xc3D\x07\x8fr"\xa1\x81')

OOYALA_API_KEY = '4za3UxOvGxUX76P98NO8TKv4aX2V.j9gKk'
OOYALA_SECRET = _decrypt('{9\x8c\xaaQ\xde\xdc\xb6+@%p\xf5\xd3l\xbd\xe2\x13\xf6utQk"\x16\xcal\xc3\xe8O9\x0bTN\x8d/I\x11Q\x90')

DEFAULT_EMAIL_SOURCE = 'Wonder PL <noreply@dev.wonderpl.com>'
EMAIL_TEMPLATE_PATH = 'templates/dolly/email'

ASSETS_URL = '//d3aiqrk3zfzlqs.cloudfront.net/static'
IMAGE_CDN = 'http://media.dev.wonderpl.com'
S3_BUCKET = 'media.dev.wonderpl.com'

VIDEO_S3_BUCKET = 'video.dev.wonderpl.com'

SENTRY_USER = _decrypt('ga\x8c\x90s97\xf4\x91u\xbf6\xfc\xf5\x12\xad\x1b\x81\x17o\xa2b-\x16b(\x9b\xd1\xff+\x01w')
SENTRY_PASSWORD = _decrypt('2N=PN0\xd0{1{\x1c\x10\x18T\x96\x1e\xaag\x17\xed\x1f\xb8\xcdGl\xdc\xc2VX\xed\x01H')
SENTRY_DSN = 'https://%s:%s@sentry.dev.rockpack.com/5' % (SENTRY_USER, SENTRY_PASSWORD)
SENTRY_ENABLE_LOGGING = 30  # logging.WARNING

ELASTICSEARCH_URL = 'http://es1:9200'

STATSD_HOST = 'admin'

ENABLE_TIMINGS = True

ENABLED_LOCALES = ('en-us',)

ADMIN_NAME = 'Wonder Place Admin'
IOS_APP_URL_SCHEME = 'wonderpldev'

DEFAULT_PROFILE_COVERS = ['default%df.jpg' % i for i in range(1, 5)]

FAVOURITE_CHANNEL = 'Favorites', 'My favorite videos', ''
WATCH_LATER_CHANNEL = 'Watch Later', '', ''

FACEBOOK_APP_ID = '573323026048639'
FACEBOOK_APP_SECRET = _decrypt('0\xa9\xf4=)\xa9\x0cC#\xda \xa2\xe1.\xf8)R\x04\xf4\x9b\x0c\xb9x\x0f\xc1\xb7\xd5\xfb=\xfb\xef\xc1')
FACEBOOK_APP_NAMESPACE = 'wonderpl-dev'

SERVER_NAME = 'dev.wonderpl.com'
SECURE_SUBDOMAIN = 'secure'
ADMIN_SUBDOMAIN = 'secure'
DEFAULT_SUBDOMAIN = 'lb'
API_SUBDOMAIN = 'api'
SHARE_SUBDOMAIN = 'share'

GOOGLE_ANALYTICS_ACCOUNT = 'UA-46534300-2'

ROMEO_ACCOUNT_VERIFY_URL = 'https://romeo.dev.wonderpl.com/_verify_account'
ROMEO_WS_URL = 'https://romeo.dev.wonderpl.com/api'

# For app store links
PHG_AFFILIATE_TOKEN = '11lukG'
ITUNES_APP_ID = '824769819'
ITUNES_APP_LINK = 'https://itunes.apple.com/app/wonder-pl/id%s?mt=8&ls=1&at=%s' % (ITUNES_APP_ID, PHG_AFFILIATE_TOKEN)

APNS_CERT_NAME = 'apns-dolly-dev.pem'
APNS_PASSPHRASE = 'wonder'

AUTH_HEADER_SANITY_CHECK = True

SQS_CRON_QUEUE = 'dolly-mainsite-cron'
SQS_EMAIL_QUEUE = 'dolly-mainsite-email'
SQS_BACKGROUND_QUEUE = 'dolly-mainsite-background'
SQS_ELASTICSEARCH_QUEUE = 'dolly-mainsite-es'

DISABLED_CRON_JOBS = (
    'import_google_movies', 'import_itunes_downloads', 'process_broadcast_messages',
    'refresh_pubsubhubbub_subscriptions', 'reset_expiring_tokens',
    'send_reactivation_emails', 'update_apns_tokens', 'update_recommender'
)

AUTO_FOLLOW_USERS = ('iOPtuNUO15f1cgMhZdDgwg',)

# Mapping from share object type to message (can have formatting)
SHARE_MESSAGE_MAP = dict(
    video_instance=dict(
        message=u"I found \"{0[title]}\" on Wonder PL and thought you might like it too.",
        message_email=u"I found \"{0[title]}\" on Wonder PL and thought you might like it too.",
        message_twitter=u"What a wonderful video! @WeAreWonderPL",
        message_facebook=u"Look what I found on Wonder PL",
    ),
    channel=dict(
        message=u"I think you're going to love the video collection \"{0[title]}\" on Wonder PL.",
        message_email=u"I think you're going to love the video collection \"{0[title]}\" on Wonder PL.",
        message_twitter=u"What a wonderful collection of videos! @WeAreWonderPL",
        message_facebook=u"I found this great collection of videos on Wonder PL",
    ),
)

PUSH_NOTIFICATION_MAP = dict(
    joined=('user', "Your friend %@ has joined Wonder PL"),
    channel_shared=('channel', '%@ shared a collection with you'),
    video_shared=('video', '%@ shared a video with you'),
)
