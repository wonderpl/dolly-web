from iso8601.iso8601 import UTC

from sqlalchemy import types
from sqlalchemy.dialects.mysql.base import MySQLDialect

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
