import base64
import uuid
import hashlib
from iso8601.iso8601 import UTC

from sqlalchemy import types
from sqlalchemy.dialects.mysql.base import MySQLDialect


class PKPrefixLengthError(Exception):
    pass


def make_id(prefix=''):
    """ Creates an id up to 24 chars long (20 without prefix) """
    if prefix and not isinstance(prefix, str) and not len(prefix) == 2:
        raise PKPrefixLengthError('{} prefix is not 2 chars'
                                  'in length or string'.format(prefix))
    return prefix + base64.urlsafe_b64encode(uuid.uuid4().bytes)[:-2]


def add_base64_pk(mapper, connection, instance, prefix=''):
    if not instance.id:
        instance.id = make_id(prefix=prefix)


def gen_videoid(locale, source, source_id):
    prefix = locale.split('-')[1].upper() if locale else 'RP'
    hash = base64.b32encode(hashlib.sha1(source_id).digest())
    return '%s%06X%s' % (prefix, source, hash)


def add_video_pk(mapper, connection, instance):
    """ set up the primary key """
    if not instance.id:
        instance.id = gen_videoid(None, instance.source, instance.source_videoid)


def add_video_meta_pk(mapper, connection, instance):
    if not instance.id:
        instance.id = gen_videoid(instance.locale, instance.video_rel.source, instance.video_rel.source_videoid)


def timezone_aware(dt):
    """ Determine if datetime is tz aware.

    >>> timezone_aware(datetime.datetime.now())
    False
    >>> timezone_aware(datetime.datetime.now(UTC))
    True

    """
    return (hasattr(dt, 'tzinfo') and dt.tzinfo is not None) and dt.tzinfo.utcoffset(dt) is not None


class UTCCoercingDateTime(types.TypeDecorator):
    impl = types.DateTime

    def process_bind_param(self, value, dialect):
        if (value is not None and isinstance(dialect, MySQLDialect)
                and timezone_aware(value)):
            value = value.astimezone(UTC).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and not timezone_aware(value):
            try:
                value = value.replace(tzinfo=UTC)
            except TypeError:
                pass
        return value

TZDateTime = UTCCoercingDateTime
