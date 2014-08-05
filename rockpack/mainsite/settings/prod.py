import os

_decrypt = lambda x: x
try:
    # Try to load _decrypt function from ROCKPACK_SETTINGS file
    execfile(os.environ['ROCKPACK_SETTINGS'])
except (IOError, KeyError):
    pass


SECRET_KEY = _decrypt('\xf0\xf9+(\x1f\x84\x06\xa84\x1b\xc6\x1d\xc4m\xc6F\xc9\xf7W\xd9\xc0b%\x9a#\x95\xc4\x1f\x8e\xe4_w\xa5\xf4\x87\xc4\xf3\x1a\xc2,\x05)h\x9d\xc9\x81\x13L\x1a\x19\xfd x?\xea\x7f\x82\xf99W]v\x87\xed')

DB_PASSWORD = _decrypt('\xf1\x13<{\xc6U^\xc8\xbdY')
DATABASE_URL = 'postgresql://mainsite:%s@db1.ec2.us.rockpack.com/rockpack' % DB_PASSWORD
SLAVE_DATABASE_URL = DATABASE_URL.replace('db1', 'db2')

GOOGLE_CONSUMER_KEY = '981375550038-9kntj6ktabchpfouhvi8hpq082j7m3rd.apps.googleusercontent.com'
GOOGLE_CONSUMER_SECRET = _decrypt('\xb1u#\xfd-\xbf\xb3\xcb\xf7\xfc1~\xc2m&I\xab\x93+\xc0%\x9eOB')

OOYALA_SECRET = _decrypt('\x9eA\xca\x87\x83\xe0\xdf\r\x82H<\xb6\x8a\x87\xb4 B\xb5\xb5\x82$\x06x\xd2\xe5>P\x82\xb1^\x91J\xa9\xcb]\x89L\x92\xc4i')

ASSETS_URL = '//d1ndbcg4lpnkzx.cloudfront.net/static'
IMAGE_CDN = 'http://media.us.rockpack.com'
S3_BUCKET = 'media.us.rockpack.com'

SENTRY_USER = '3edf45f0b76d47f39ea4905efbda4da3'
SENTRY_PASSWORD = _decrypt('\xf8\xdfi\xda\x04\xbb\x05I\x1fpMx\xa0\xf1\xac\xd4\x84\xa2\xaeP\xd3\x9aN\xa0\xc6C\x92>\x8b\x1a\x07\xd8')
SENTRY_DSN = 'https://%s:%s@sentry.dev.rockpack.com/3' % (SENTRY_USER, SENTRY_PASSWORD)
SENTRY_ENABLE_LOGGING = 30  # logging.WARNING

ELASTICSEARCH_URL = 'http://localhost:9200'

ENABLE_BACKGROUND_SQS = True
SQS_REGION = 'us-east-1'

STATSD_HOST = 'admin'

ENABLE_TIMINGS = True

DISABLED_CRON_JOBS = ('update_user_promotions', 'process_video_instance_queue')

# Credentials for rockpack prod app on facebook
FACEBOOK_APP_ID = '217008995103822'
FACEBOOK_APP_SECRET = _decrypt('\xab\x08"\xcc\xab\xc1P\x96W\xc5G\x94+\x96DV\x13@\xc375i\xc1\x1fmJ)\x08\x97\xab"<')
FACEBOOK_APP_NAMESPACE = 'rockpack'

SERVER_NAME = 'rockpack.com'
SECURE_SUBDOMAIN = 'secure'
ADMIN_SUBDOMAIN = 'admin'
DEFAULT_SUBDOMAIN = 'lb.us'
API_SUBDOMAIN = 'api'
SHARE_SUBDOMAIN = 'share'

GOOGLE_ANALYTICS_ACCOUNT = 'UA-38220268-5'

APNS_PUSH_TYPE = 'push_production'
APNS_FEEDBACK_TYPE = 'feedback_production'
APNS_CERT_NAME = 'apns-prod.pem'
APNS_PASSPHRASE = _decrypt('\xff\x15\x15\x97\xb2;{\x9a\xe8\x18')

ITUNES_CONNECT_VENDORID = '85709520'
ITUNES_CONNECT_APPLEID = 'bot@rockpack.com'
ITUNES_CONNECT_PASSWORD = _decrypt('\xaf\x11\x0e\xce\r&a\xd0mV')

MYRRIX_URL = 'http://recommender:9400'
