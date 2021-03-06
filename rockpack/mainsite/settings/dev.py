import os

_decrypt = lambda x: x
try:
    # Try to load _decrypt function from ROCKPACK_SETTINGS file
    execfile(os.environ['ROCKPACK_SETTINGS'])
except (IOError, KeyError):
    pass


SECRET_KEY = _decrypt('&\xa9C\xe3<j\x0f\xe3\xe6\x8e\t\x04\x81\x1d[b\x87\xcf2\xe4U\x90\x00d\x004\x9d2\xfa\xff\x19\xfc\x9cH\x98PX7\xbfh\xec\x08{LTr|\xae\x92u\x04+\x9a\xe5\x8e\x17\xear\x9c\x02\x1c\x97\xe3\x8c')

DB_PASSWORD = _decrypt('(\x80JE\x9b\xd7\xb0\xd9')
DATABASE_URL = 'postgresql://mainsite:%s@db1/rockpack' % DB_PASSWORD

GOOGLE_CONSUMER_KEY = '981375550038-dbckr7s2hb5rsaohj9j4fhl0cbu4col7.apps.googleusercontent.com'
GOOGLE_CONSUMER_SECRET = _decrypt('#w\x81\xcf\x95K "\xe3\x10\xa8\xd0\x84\xf9\xee\xe5\xea]\x90\x9dw\x9b\xd9\xb2')

OOYALA_SECRET = _decrypt('\x12\x80[\x94o\xa1\xbeE\xa5<\xef\xfc\x81\rc\xbb{\x8b\n\xe4\x992-X\xb2\x993\r\xeb\xe6|\xc0\x14=R\x9apAth')

ASSETS_URL = '//dm4udhbt1x280.cloudfront.net/static'
IMAGE_CDN = 'http://media.dev.rockpack.com'
S3_BUCKET = 'media.dev.rockpack.com'

SENTRY_USER = _decrypt('#\x13\xf7\x06\x8f\x0c:+\x90\xcdD\xd2 \xd3sv\xec\xb8\xb8\x1e86\xd1E\xf0\x0b\xa6\xca\xc4\xc2\ng')
SENTRY_PASSWORD = _decrypt('r\x0e\xba+q\xd9\x13Mt1\x14\xdc\x14)\xdf\x97\xfbQ\xb6\xa2Q:\xb3Tu,\x8a \x15\xb1\x0e\xc0')
SENTRY_DSN = 'https://%s:%s@sentry.dev.rockpack.com/2' % (SENTRY_USER, SENTRY_PASSWORD)
SENTRY_ENABLE_LOGGING = 30  # logging.WARNING

ELASTICSEARCH_URL = 'http://es1:9200'

ENABLE_BACKGROUND_SQS = True

DISABLED_CRON_JOBS = (
    'import_google_movies', 'import_itunes_downloads', 'process_broadcast_messages',
    'refresh_pubsubhubbub_subscriptions', 'reset_expiring_tokens',
    'send_reactivation_emails', 'update_apns_tokens', 'update_recommender'
)

STATSD_HOST = 'admin'

ENABLE_TIMINGS = True
