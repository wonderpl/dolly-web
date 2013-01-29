import os
import base64
import uuid
from PIL import Image

from rockpack.mainsite.core.s3 import S3Uploader
from rockpack.mainsite.core.s3 import jpeg_policy


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

    def crop_and_scale(self, img, w, h):
        old_w, old_h = img.size
        new_w, new_h = w, h
        old_ratio = float(old_w) / float(old_h)
        new_ratio = float(new_w) / float(new_h)

        if new_ratio < old_ratio:
            crop_height = old_h
            crop_width = crop_height * new_ratio
            x_offset = int(float(old_w-crop_width) / 2)
            y_offset = 0
        else:
            crop_width = old_w
            crop_height = crop_width / new_ratio
            x_offset = 0
            y_offset = int(float(old_h-crop_height) / 3)

        new_img = img.crop(
            (x_offset,
                y_offset,
                x_offset+int(crop_width),
                y_offset+int(crop_height)))

        return new_img.resize((w, h,), Image.ANTIALIAS)

    def resize(self, image_path=None, f_obj=None):
        if not self.configuration:
            raise self.ConfigurationMissingError

        if not self.image_path and not image_path and not f_obj:
            raise self.ImagePathMissingError

        if image_path or f_obj:
            self.image_path = image_path or f_obj


        img = Image.open(self.image_path)
        resized = {}
        for name, sizing in self.configuration.iteritems():
            new_img = self.crop_and_scale(img, sizing[0], sizing[1])
            resized.update({name: new_img})

        return resized


class ImageUploader(object):

    uploader = None

    def __init__(self, uploader=S3Uploader):
        self.uploader = uploader()

    def from_file(self, fp, target_path=None, target_filename=None, extension=None):

        # Construct a new filename
        if not target_filename:
            target_filename = base64.urlsafe_b64encode(
                uuid.uuid4().bytes)[:-2]

        if extension:
            target_filename += '.' + extension

        # Create a `key` from a target "path" and the filename
        key_name = os.path.join(target_path, target_filename)

        self.uploader.put_from_file(fp, key_name, headers=jpeg_policy)
        return key_name
