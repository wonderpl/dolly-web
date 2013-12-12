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

OOYALA_SECRET = _decrypt('UE\xec\x0c\xfe\x00\x0c\x84\xa1\x88\xf3<\xbc\x19</\x18s4\x8a\xa5#\xec\x0e\x89\xa3\xb7\x15\xc0i\xaeS~\x8f#5\xc4\xea\xab\x96')

#ASSETS_URL = '//dolly.dev.rockpack.com/static'
IMAGE_CDN = 'http://media.dolly.dev.rockpack.com'
S3_BUCKET = 'media.dolly.dev.rockpack.com'

SENTRY_USER = _decrypt('ga\x8c\x90s97\xf4\x91u\xbf6\xfc\xf5\x12\xad\x1b\x81\x17o\xa2b-\x16b(\x9b\xd1\xff+\x01w')
SENTRY_PASSWORD = _decrypt('2N=PN0\xd0{1{\x1c\x10\x18T\x96\x1e\xaag\x17\xed\x1f\xb8\xcdGl\xdc\xc2VX\xed\x01H')
SENTRY_DSN = 'https://%s:%s@sentry.dev.rockpack.com/5' % (SENTRY_USER, SENTRY_PASSWORD)
SENTRY_ENABLE_LOGGING = 30  # logging.WARNING

ELASTICSEARCH_URL = 'http://es1:9200'

ASYNC_ES_VIDEO_UPDATES = True

STATSD_HOST = 'admin'

ENABLE_TIMINGS = True

#USE_GEVENT = True

ADMIN_NAME = 'Dolly Admin'

FACEBOOK_APP_ID = '573323026048639'
FACEBOOK_APP_SECRET = _decrypt('0\xa9\xf4=)\xa9\x0cC#\xda \xa2\xe1.\xf8)R\x04\xf4\x9b\x0c\xb9x\x0f\xc1\xb7\xd5\xfb=\xfb\xef\xc1')
FACEBOOK_APP_NAMESPACE = 'dolly-dev'

#SERVER_NAME = 'dev.rockpack.com'
#SECURE_SUBDOMAIN = 'secure'
#ADMIN_SUBDOMAIN = 'dolly'
#DEFAULT_SUBDOMAIN = 'lb'
#API_SUBDOMAIN = 'api'
#SHARE_SUBDOMAIN = 'share'

AUTH_HEADER_SANITY_CHECK = True

SQS_CRON_QUEUE = 'dolly-mainsite-cron'
SQS_EMAIL_QUEUE = 'dolly-mainsite-email'
SQS_VIDEO_UPDATE_QUEUE = 'dolly-mainsite-es'
