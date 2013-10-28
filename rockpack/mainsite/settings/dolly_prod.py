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

#ASSETS_URL = '//d1ndbcg4lpnkzx.cloudfront.net/static'
IMAGE_CDN = 'http://media.dolly.us.rockpack.com'
S3_BUCKET = 'media.dolly.us.rockpack.com'

SENTRY_USER = _decrypt('t\x0e\x82\x02\xcc\xbf\x8d\x02<d\xf5\xd8\xdc\x96(fJ\xb0\\v!\x9b].g\xcd\xbc\xc2 lt\xff')
SENTRY_PASSWORD = _decrypt('v\xb6a:\x0b\xb2\x88\x18z\xcc\xe1N\xe2N\xf5\x19\xe8\xfcXq\xe2\x9c;\xe0S\x8eg\n\xa9\x03\x97\r')
SENTRY_DSN = 'https://%s:%s@sentry.dev.rockpack.com/4' % (SENTRY_USER, SENTRY_PASSWORD)
SENTRY_ENABLE_LOGGING = 30  # logging.WARNING

#ELASTICSEARCH_URL = 'http://localhost:9200'

ASYNC_ES_VIDEO_UPDATES = True

STATSD_HOST = 'admin'

ENABLE_TIMINGS = True

SQS_REGION = 'us-east-1'

#USE_GEVENT = True

ADMIN_NAME = 'Dolly Admin'

FACEBOOK_APP_ID = '517447921656577'
FACEBOOK_APP_SECRET = _decrypt('#>d\xb3\ri\xc5\x07*\xb7\x99\xb05\x0f8\x19\x03\xff1\xb3Id\xab=\x13\xc9\xcfQD\x0c\xd2G')
FACEBOOK_APP_NAMESPACE = 'dollyns'

SERVER_NAME = 'rockpack.com'
SECURE_SUBDOMAIN = 'secure'
ADMIN_SUBDOMAIN = 'dolly'
DEFAULT_SUBDOMAIN = 'lb.us'
API_SUBDOMAIN = 'api'
SHARE_SUBDOMAIN = 'share'

#GOOGLE_ANALYTICS_ACCOUNT = 'UA-38220268-5'
#
#APNS_PUSH_TYPE = 'push_production'
#APNS_FEEDBACK_TYPE = 'feedback_production'
#APNS_CERT_NAME = 'apns-prod.pem'
#APNS_PASSPHRASE = _decrypt('\xff\x15\x15\x97\xb2;{\x9a\xe8\x18')
#
#ITUNES_CONNECT_VENDORID = '85709520'
#ITUNES_CONNECT_APPLEID = 'bot@rockpack.com'
#ITUNES_CONNECT_PASSWORD = _decrypt('\xaf\x11\x0e\xce\r&a\xd0mV')

SQS_CRON_QUEUE = 'dolly-mainsite-cron'
SQS_EMAIL_QUEUE = 'dolly-mainsite-email'
SQS_VIDEO_UPDATE_QUEUE = 'dolly-mainsite-es'
