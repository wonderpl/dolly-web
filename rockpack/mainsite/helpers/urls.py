import urlparse
from flask import current_app


def image_url_from_path(path):
    return urlparse.urljoin(current_app.config['IMAGE_CDN'], path)
