import boto
from flask import current_app


def s3_connection():
    return boto.connect_s3(
            current_app.config['AWS_ACCESS_KEY'],
            current_app.config['AWS_SECRET_KEY'])


def s3_upload(filename, _file, path, acl='public-read'):
    conn = s3_connection()
    bucket = conn.get_bucket(current_app.config['S3_BUCKET'])

    new_file = bucket.new_key('/'.join([path, filename]))
    new_file.set_contents_from_string(_file.readlines())
    new_file.set_acl(acl)

    return filename


def path_to_asset():
    return current_app.config['S3_BUCKET'] + '.s3.amazonaws.com' # HACK!


def full_thumbnail_path(filename):
    return '/'.join(['http://',
        path_to_asset(),
        current_app.config['S3_THUMBNAIL_DIR'],
        filename
        ])


def thumbnail_upload(filename, _file):
    return s3_upload(
            filename,
            _file,
            current_app.config['S3_THUMBNAIL_DIR'])
