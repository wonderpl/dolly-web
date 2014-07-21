# load _decrypt function from ROCKPACK_SETTINGS file
import os
execfile(os.environ['ROCKPACK_SETTINGS'])

DOLLY = True

SECRET_KEY = _decrypt('tW\xa3\xbb\xb6\x957\xa1\xef\xc5l{\xcf)@\x18u\xc8\xe1\x03j\xcbL\xa8gt\xaffp\xf7aN\xef\xdf\xf7j\'\xce\xd0z\xb7\x99\x8dA\xecZ\xcbF\n\x8b\xd7\xd7nQ\x91?\xc1\xe5\xf8+R\xde\xcb\xdc')

DB_PASSWORD = _decrypt('\x7fP[\x7f$9%\x01~{')
DATABASE_URL = 'postgresql://mainsite:%s@db1/dolly' % DB_PASSWORD
SLAVE_DATABASE_URL = DATABASE_URL.replace('db1', 'db2')

GOOGLE_CONSUMER_KEY = '981375550038-9kntj6ktabchpfouhvi8hpq082j7m3rd.apps.googleusercontent.com'
GOOGLE_CONSUMER_SECRET = _decrypt('?\xacR[\xb5N\xe3P\xd4\xea\x85\x1e\x89\xd08o\xd8\xfcI\xb8\xceO^k')

OOYALA_SECRET = _decrypt('\x10\xa2u\xb8\xc5\xae\x86\x07!\r\xfe\x12l}\xdb~Z\x0ekOI\x9f\x8f\xb9\x8e\xc9\xb7\xc4!\xea~H<\xbf\xde\xcb\xb3\x12~\xa2')

DEFAULT_EMAIL_SOURCE = 'Wonder PL <noreply@wonderpl.com>'
EMAIL_TEMPLATE_PATH = 'templates/dolly/email'

REACTIVATION_THRESHOLD_DAYS = 0
PING_EMAILS = [
    dict(
        listid=1,
        threshold_days=2,
        template_path='day-two.html',
        tracking_params=dict(utm_medium='email', utm_campaign='p2'),
    ),
    dict(
        listid=1,
        threshold_days=9,
        template_path='hints-and-tips.html',
        tracking_params=dict(utm_medium='email', utm_campaign='p9'),
    )
]

ASSETS_URL = '//d1ndbcg4lpnkzx.cloudfront.net/static'
IMAGE_CDN = 'http://media.us.wonderpl.com'
S3_BUCKET = 'media.us.wonderpl.com'

VIDEO_S3_BUCKET = 'video.us.wonderpl.com'

SENTRY_USER = _decrypt('t\x0e\x82\x02\xcc\xbf\x8d\x02<d\xf5\xd8\xdc\x96(fJ\xb0\\v!\x9b].g\xcd\xbc\xc2 lt\xff')
SENTRY_PASSWORD = _decrypt('v\xb6a:\x0b\xb2\x88\x18z\xcc\xe1N\xe2N\xf5\x19\xe8\xfcXq\xe2\x9c;\xe0S\x8eg\n\xa9\x03\x97\r')
SENTRY_DSN = 'https://%s:%s@sentry.dev.rockpack.com/4' % (SENTRY_USER, SENTRY_PASSWORD)
SENTRY_ENABLE_LOGGING = 30  # logging.WARNING

ELASTICSEARCH_URL = 'http://localhost:9200'

STATSD_HOST = 'admin'

ENABLE_TIMINGS = True

SQS_REGION = 'us-east-1'

ENABLED_LOCALES = ('en-us',)

ADMIN_NAME = 'Wonder Place Admin'
IOS_APP_URL_SCHEME = 'wonderpl'

DEFAULT_PROFILE_COVERS = ['default%df.jpg' % i for i in range(1, 5)]

FAVOURITE_CHANNEL = 'Favorites', 'My favorite videos', ''
WATCH_LATER_CHANNEL = 'Watch Later', '', ''

FACEBOOK_APP_ID = '517447921656577'
FACEBOOK_APP_SECRET = _decrypt('#>d\xb3\ri\xc5\x07*\xb7\x99\xb05\x0f8\x19\x03\xff1\xb3Id\xab=\x13\xc9\xcfQD\x0c\xd2G')
FACEBOOK_APP_NAMESPACE = 'wonderpl'

TWITTER_CONSUMER_KEY = 'tB2PungXx7mbcHAA3zICQbz2w'
TWITTER_CONSUMER_SECRET = _decrypt('~8qE!G\xb0\xd2\x10\xa8lV\x0e\x07z\x87\x82,[+Z\xae\xe0u\xd1\xe0\x1b\xa9\xf1\x00\xd0v9\xbe!\xf9\x81\xa8\xf00\xf4\x1b\x98:\x1f\xed\xa5Ss+')
TWITTER_ACCESS_TOKEN_KEY = '2342156982-IGwPLKAt7c09ue2XrXlB6UNG4dUwgeo4NBonusW'
TWITTER_ACCESS_TOKEN_SECRET = _decrypt('6c\x9ap\x18\x10\xc8\x84Bh\xdd#\x02\xb6QJ\x83\xdf}k\xff\x9d\xb3\xfc2\x06H\x1e\x07@\xcf.|{;\xfa\xd0\x89\x80URO\x0b\xc4\xc9')

MAILCHIMP_TOKEN = _decrypt('~M\x93$\xd3\xbb\xf4Q\xba\xe0\xf2\x9b@"\xe5\xd9\xe4\xca\xc1o\x98y\xa2\xfe\xb9;\x14O\xb46~\xc1\xbb\xc7\xe7\\')
MAILCHIMP_LISTID = '74e1537b36'

SERVER_NAME = 'wonderpl.com'
SECURE_SUBDOMAIN = 'secure'
ADMIN_SUBDOMAIN = 'admin'
DEFAULT_SUBDOMAIN = 'lb.us'
API_SUBDOMAIN = 'api'
SHARE_SUBDOMAIN = 'share'

GOOGLE_ANALYTICS_ACCOUNT = 'UA-46520786-2'

# For app store links
PHG_AFFILIATE_TOKEN = '11lukG'
ITUNES_APP_ID = '824769819'
ITUNES_APP_LINK = 'https://itunes.apple.com/app/wonder-pl/id%s?mt=8&ls=1&at=%s' % (ITUNES_APP_ID, PHG_AFFILIATE_TOKEN)

APNS_PUSH_TYPE = 'push_production'
APNS_FEEDBACK_TYPE = 'feedback_production'
APNS_CERT_NAME = 'apns-dolly-prod.pem'
APNS_PASSPHRASE = _decrypt('\x1dd\xdf\xce\xe0\x10\x170sP')

ITUNES_CONNECT_VENDORID = '86088300'
ITUNES_CONNECT_APPLEID = 'bot@wonderpl.com'
ITUNES_CONNECT_PASSWORD = _decrypt('\x01\xbdZBAe\x87I\xd3\xcf')

SQS_CRON_QUEUE = 'dolly-mainsite-cron'
SQS_EMAIL_QUEUE = 'dolly-mainsite-email'
SQS_BACKGROUND_QUEUE = 'dolly-mainsite-background'
SQS_ELASTICSEARCH_QUEUE = 'dolly-mainsite-es'

DISABLED_CRON_JOBS = ('import_google_movies', 'update_recommender')

AUTO_FOLLOW_USERS = ('iOPtuNUO15f1cgMhZdDgwg',)

ENABLE_USER_CATEGORISATION_CONDITIONS = True

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

AUTO_TAG_CHANNELS = {
    'ch-d8Wwdt9mA5LImofAB6CdA': 'cat-editors-picks',
}
