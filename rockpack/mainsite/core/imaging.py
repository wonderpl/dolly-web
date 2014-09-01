import os
import base64
import uuid
from PIL import Image
from wonder.common.imaging import resize
from rockpack.mainsite.core import s3


class Resizer(object):

    class ConfigurationMissingError(Exception):
        pass

    class ConfigurationInvalid(Exception):
        pass

    class ImagePathMissingError(Exception):
        pass

    class FileDoesNotExist(Exception):
        pass

    configuration = {}
    image_path = ''

    def __init__(self, configuration):
        """ Takes a `configuration` which is
            a dict of keys (a name) and values
            (tuple of width and height) """

        if not configuration or not isinstance(configuration, dict):
            raise self.ConfigurationInvalid('Must be type dict'
                                            'and not empty')
        self.configuration = configuration

    def add_configuration(self, configuration):
        self.configuration = configuration

    def path_to_image(self, path):
        if os.path.exists(path):
            self.image_path = path
            return
        raise self.FileDoesNotExist

    def resize(self, image_path=None, f_obj=None, aoi=None):
        if not self.configuration:
            raise self.ConfigurationMissingError

        if not self.image_path and not image_path and not f_obj:
            raise self.ImagePathMissingError

        if image_path or f_obj:
            self.image_path = image_path or f_obj

        self.orig_img = img = Image.open(self.image_path)
        sizes = self.configuration.items()
        return dict(resize(img, sizes, aoi))

    @property
    def original_extension(self):
        orig_ext = getattr(self.image_path, 'filename', '').rsplit('.', 1)[-1]
        if not orig_ext:
            format = self.orig_img.format
            orig_ext = next(e for e, f in sorted(Image.EXTENSION.items(), reverse=True) if f == format)[1:]
        return orig_ext


class ImageUploader(object):

    uploader = None

    def __init__(self, uploader=None):
        self.uploader = uploader() if uploader else s3.S3Uploader()

    @classmethod
    def new_filename(cls, target_path=None, target_filename=None, extension=None):
        if not target_filename:
            target_filename = base64.urlsafe_b64encode(
                uuid.uuid4().bytes)[:-2]

        if extension:
            target_filename += '.' + extension

        # Create a `key` from a target "path" and the filename
        if not target_path:
            return target_filename
        return os.path.join(target_path, target_filename)

    def from_file(self, fp, target_path=None, target_filename=None, extension=None):
        key_name = self.new_filename(target_path, target_filename, extension)
        self.uploader.put_from_file(fp, key_name, headers=s3.jpeg_policy)
        return key_name
