# load _decrypt function from ROCKPACK_SETTINGS file
import os
execfile(os.environ['ROCKPACK_SETTINGS'])


SECRET_KEY = _decrypt('&\xa9C\xe3<j\x0f\xe3\xe6\x8e\t\x04\x81\x1d[b\x87\xcf2\xe4U\x90\x00d\x004\x9d2\xfa\xff\x19\xfc\x9cH\x98PX7\xbfh\xec\x08{LTr|\xae\x92u\x04+\x9a\xe5\x8e\x17\xear\x9c\x02\x1c\x97\xe3\x8c')

DB_PASSWORD = _decrypt('}\xaa\x87\xca\xd1Xx\x99\r\x1c')
DATABASE_URL = 'postgresql://mainsite:%s@db1/rockpack' % DB_PASSWORD
#SLAVE_DATABASE_URL = None

GOOGLE_CONSUMER_KEY = '981375550038-dbckr7s2hb5rsaohj9j4fhl0cbu4col7.apps.googleusercontent.com'
GOOGLE_CONSUMER_SECRET = _decrypt('#w\x81\xcf\x95K "\xe3\x10\xa8\xd0\x84\xf9\xee\xe5\xea]\x90\x9dw\x9b\xd9\xb2')

ASSETS_URL = '//dm4udhbt1x280.cloudfront.net/static'
IMAGE_CDN = 'http://media.dev.rockpack.com'
S3_BUCKET = 'media.dev.rockpack.com'

SENTRY_USER = _decrypt('#\x13\xf7\x06\x8f\x0c:+\x90\xcdD\xd2 \xd3sv\xec\xb8\xb8\x1e86\xd1E\xf0\x0b\xa6\xca\xc4\xc2\ng')
SENTRY_PASSWORD = _decrypt('r\x0e\xba+q\xd9\x13Mt1\x14\xdc\x14)\xdf\x97\xfbQ\xb6\xa2Q:\xb3Tu,\x8a \x15\xb1\x0e\xc0')
SENTRY_DSN = 'https://%s:%s@sentry.dev.rockpack.com/2' % (SENTRY_USER, SENTRY_PASSWORD)
SENTRY_ENABLE_LOGGING = 30  # logging.WARNING

ELASTICSEARCH_URL = 'http://localhost:9200'

STATSD_HOST = 'admin'

ENABLE_TIMINGS = True

#USE_GEVENT = True

ENABLE_FULLWEB = True
