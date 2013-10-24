import os
import base64
import hashlib
import cStringIO
import wtforms as wtf
from ast import literal_eval
from sqlalchemy import types
from sqlalchemy.dialects import postgres
from rockpack.mainsite import app
from rockpack.mainsite.core import imaging
from .urls import image_url_from_path


IMAGE_CONVERSION_FORMAT = ('JPEG', 'jpg',)


class PKPrefixLengthError(Exception):
    pass


def make_id(prefix='', length=16):
    """ Creates an id up to 24 chars long (22 without prefix) """
    if prefix and not isinstance(prefix, str) and not len(prefix) == 2:
        raise PKPrefixLengthError('{} prefix is not 2 chars'
                                  'in length or string'.format(prefix))
    return prefix + base64.urlsafe_b64encode(os.urandom(length)).rstrip('=')


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


def get_column_property(model, column, prop):
    return getattr(model._sa_class_manager.mapper.get_property(column).columns[0].type, prop)


def get_column_validators(model, columnname, required=True):
    column = model._sa_class_manager.mapper.get_property(columnname).columns[0]
    validators = []
    if required and not column.nullable:
        validators.append(wtf.validators.Required())
    if hasattr(column.type, 'length'):
        validators.append(wtf.validators.Length(max=column.type.length))
    return validators


def insert_new_only(model, instances):
    """Check db for existing instances and insert new records only"""
    from rockpack.mainsite.core.dbapi import db
    all_ids = set(i.id for i in instances)
    query = db.session.query(model.id).filter(model.id.in_(all_ids))
    existing_ids = set(i.id for i in query)
    new_ids = all_ids - existing_ids
    db.session.add_all(i for i in instances if i.id in new_ids)
    return new_ids, existing_ids


def image_base(type, name):
    return '/'.join((app.config['IMAGE_BASE_PATH'], type.lower(), name, ''))


class ImageUrl(str):
    # Type is used for matching with ModelView.column_type_formatters
    pass


class ImagePath(object):
    """Wrapper around image path string that can generate thumbnail urls."""

    def __init__(self, path, type):
        self.path = path or ''
        self._type = type
        self._names = app.config['%s_IMAGES' % type]

    def __str__(self):
        return self.path

    def __nonzero__(self):
        return bool(self.path)

    def __getattr__(self, name):
        if name == 'original':
            path = self.path
        else:
            if name == 'url':
                name = 'thumbnail_medium'
            if name not in self._names:
                raise AttributeError(name)
            path = self.path.rsplit('.', 1)[0] + '.' + IMAGE_CONVERSION_FORMAT[1]
        if self.path:
            path = image_base(self._type, name) + path
            return ImageUrl(image_url_from_path(path))
        else:
            return ''


class ImageType(types.TypeDecorator):
    """VARCHAR column which stores image base path."""

    impl = types.String

    def __init__(self, cfgkey, reference_only=False):
        super(ImageType, self).__init__(1024)
        self.reference_only = reference_only
        self.cfgkey = cfgkey

    def process_result_value(self, value, dialect):
        return ImagePath(value, self.cfgkey)


class BoxType(types.TypeDecorator):

    if 'postgres' in app.config.get('DATABASE_URL', ''):
        impl = postgres.ARRAY(types.Float)
    else:
        impl = types.String

    def process_bind_param(self, value, dialect):
        if value:
            return get_box_value(value)


def get_box_value(value):
    if isinstance(value, basestring):
        value = map(float, literal_eval(value))
    assert len(value) == 4
    assert all(0 <= i <= 1 for i in value)
    return value


def resize_and_upload(fp, cfgkey, aoi=None):
    """Takes file-like object and uploads thumbnails to s3."""
    uploader = imaging.ImageUploader()
    new_name = make_id()

    # Resize images
    resizer = imaging.Resizer(app.config['%s_IMAGES' % cfgkey])
    resized = resizer.resize(fp, aoi=aoi)

    # Upload original
    orig_ext = resizer.original_extension
    uploader.from_file(fp, image_base(cfgkey, 'original'), new_name, orig_ext)

    for name, img in resized.iteritems():
        f = cStringIO.StringIO()
        img.save(f, IMAGE_CONVERSION_FORMAT[0], quality=90)
        uploader.from_file(f, image_base(cfgkey, name), new_name, IMAGE_CONVERSION_FORMAT[1])
        f.close()
    if orig_ext:
        return '.'.join([new_name, orig_ext])
    return new_name
