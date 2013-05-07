import os
import base64
import uuid
from PIL import Image
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

    def crop_and_scale(self, img, size, aoi=None):
        ow, oh = img.size
        ratio = float(size[0]) / float(size[1])

        # Find center of aoi (Area Of Interest):
        if aoi:
            x1, y1, x2, y2 = map(float, aoi)
            old_ratio = 0
        else:
            x1, y1, x2, y2 = 0.0, 0.0, 1.0, 1.0
            old_ratio = float(ow) / float(oh)
        centerX = (x2 + x1) * ow / 2
        centerY = (y2 + y1) * oh / 2
        print 'aoi', aoi

        # Define (dx, dy), the crop boundaries:
        if (aoi and ratio < 1) or (old_ratio and ratio > old_ratio):
            # portrait
            dx = (x2 - x1) * ow / 2
            dy = dx / ratio
        elif (aoi and ratio > 1) or (old_ratio):
            # landscape
            dy = (y2 - y1) * oh / 2
            dx = dy * ratio
        else:
            # square, using the 16:9 height as boundary
            dx = (x2 - x1) * ow / 2 / 9 * 16
            dy = dx

        # Define the crop bounding box:
        dx1 = centerX - dx
        dy1 = centerY - dy
        dx2 = centerX + dx
        dy2 = centerY + dy

        # Shift crop bounding box to fit within source image:
        if dx1 < 0:
            dx2 = min(dx2 - dx1, ow)
            dx1 = 0
        if dx2 > ow:
            dx1 = max(dx1 - (dx2 - ow), 0)
            dx2 = ow
        if dy1 < 0:
            dy2 = min(dy2 - dy1, oh)
            dy1 = 0
        if dy2 > oh:
            dy1 = max(dy1 - (dy2 - oh), 0)
            dy2 = oh

        return img.crop(map(int, (dx1, dy1, dx2, dy2))).resize(size, Image.ANTIALIAS)

    def resize(self, image_path=None, f_obj=None, aoi=None):
        if not self.configuration:
            raise self.ConfigurationMissingError

        if not self.image_path and not image_path and not f_obj:
            raise self.ImagePathMissingError

        if image_path or f_obj:
            self.image_path = image_path or f_obj

        self.orig_img = img = Image.open(self.image_path)
        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGBA')
        resized = {}
        for name, sizing in self.configuration.iteritems():
            new_img = self.crop_and_scale(img, (sizing[0], sizing[1]), aoi)
            resized.update({name: new_img})

        return resized

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
