import urlparse
import cStringIO
from flask import current_app
from rockpack.mainsite.core import imaging
from rockpack.mainsite.helpers.db import make_id


def image_url_from_path(path):
    return urlparse.urljoin(
        current_app.config['IMAGE_CDN'],
        path)


def resize_and_upload(f_obj, img_resize_config, img_path_config):
    # TODO: move this somewhere more intelligent
    f = cStringIO.StringIO()
    f.write(f_obj.stream.read())
    f.seek(0)
    new_name = make_id()

    # Resize images
    resizer = imaging.Resizer(img_resize_config)
    resized = resizer.resize(f)

    # Upload original
    uploader = imaging.ImageUploader()
    uploader.from_string(f, target_path=img_path_config['original'], target_filename=new_name)

    new_name += '.jpg'
    for name, img in resized.iteritems():
        f = cStringIO.StringIO()
        img.save(f, 'JPEG', quality=90)
        f.seek(0)

        uploader.from_string(f, target_path=img_path_config[name], target_filename=new_name)
        f.close()
    return new_name
