import urlparse
from flask import current_app, url_for as _url_for


def url_for(*args, **kwargs):
    kwargs.setdefault('_external', True)
    url = _url_for(*args, **kwargs)
    # Ensure urls on secure domain use https:
    secure_subdomain = current_app.config.get('SECURE_SUBDOMAIN')
    if secure_subdomain and url.startswith('http://' + secure_subdomain + '.'):
        url = 'https://' + url[7:]
    return url


def image_url_from_path(path):
    return urlparse.urljoin(current_app.config['IMAGE_CDN'], path)
