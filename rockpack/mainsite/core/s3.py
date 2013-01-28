import datetime
import boto
from flask import current_app


jpeg_policy = {'Expires': datetime.datetime.utcnow() + datetime.timedelta(days=(60 * 365)),
        'Content-Type': 'image/jpeg',
        'Cache-Control': 'max-age={}'.format((60*60*24*365*60))}


class S3Uploader(object):

    def __init__(self):
        self.conn = self._connection()
        self.bucket = self.conn.get_bucket(current_app.config['S3_BUCKET'])

    @staticmethod
    def _connection():
        return boto.connect_s3(
            current_app.config['AWS_ACCESS_KEY'],
            current_app.config['AWS_SECRET_KEY'])

    def exists(self, name):
        if self.bucket.get_key(name):
            return True
        return False

    def get_file(self, name):
        f = self.bucket.get_key(name)
        if f:
            return f.get_contents_as_string()
        return None

    def put_from_file(self, file_path, key_name,
                      acl='public-read', replace=False, headers=None):

        new_file = self.bucket.new_key(key_name)
        new_file.set_contents_from_filename(file_path, policy=acl, replace=replace, headers=headers)
