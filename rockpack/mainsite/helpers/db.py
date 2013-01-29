import base64
import uuid
import hashlib
import cStringIO
from iso8601.iso8601 import UTC
from sqlalchemy import types
from sqlalchemy.dialects.mysql.base import MySQLDialect
from flask import current_app
from rockpack.mainsite.core import imaging
from .urls import image_url_from_path


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


class ImageUrl(str):
    # Type is used for matching with ModelView.column_type_formatters
    pass


class ImagePath(object):
    """Wrapper around image path string that can generate thumbnail urls."""

    def __init__(self, path, pathmap):
        self.path = path
        self.pathmap = pathmap

    def __str__(self):
        return self.path

    def __getattr__(self, name):
        try:
            base = self.pathmap[name]
        except KeyError, e:
            raise AttributeError(e.message)
        else:
            url = image_url_from_path(base + self.path)
            return ImageUrl(url)


class ImageType(types.TypeDecorator):
    """VARCHAR column which stores image base path."""

    impl = types.String

    def __init__(self, cfgkey):
        super(ImageType, self).__init__(1024)
        self.cfgkey = cfgkey

    def process_bind_param(self, value, dialect):
        if value:
            value = resize_and_upload(value, self.cfgkey)
        return value

    def process_result_value(self, value, dialect):
        return ImagePath(value, current_app.config['%s_IMG_PATHS' % self.cfgkey])


def resize_and_upload(fp, cfgkey):
    """Takes file-like object and uploads thumbnails to s3."""
    uploader = imaging.ImageUploader()

    img_resize_config = current_app.config['%s_IMAGES' % cfgkey]
    img_path_config = current_app.config['%s_IMG_PATHS' % cfgkey]

    new_name = make_id()

    # Resize images
    resizer = imaging.Resizer(img_resize_config)
    resized = resizer.resize(fp)

    # Upload original
    orig_ext = getattr(fp, 'filename', '').rsplit('.', 1)[-1]
    uploader.from_file(fp, img_path_config['original'], new_name, orig_ext)

    for name, img in resized.iteritems():
        f = cStringIO.StringIO()
        img.save(f, 'JPEG', quality=90)
        uploader.from_file(f, img_path_config[name], new_name, 'jpg')
        f.close()
    return new_name + '.jpg'
