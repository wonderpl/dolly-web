import urlparse
from werkzeug.exceptions import NotFound
from flask import current_app, url_for as _url_for


def url_for(*args, **kwargs):
    kwargs.setdefault('_external', True)
    url = _url_for(*args, **kwargs)
    # Ensure urls on secure domain use https:
    secure_subdomain = current_app.config.get('SECURE_SUBDOMAIN')
    if secure_subdomain and url.startswith('http://' + secure_subdomain + '.'):
        url = 'https://' + url[7:]
    return url


def url_to_endpoint(url):
    url = urlparse.urlsplit(url)
    # XXX: Revisit this and double-check this is "the right thing"!
    matcher = current_app.url_map.bind(url.netloc)
    matcher.subdomain = current_app.config.get('API_SUBDOMAIN') or ''
    try:
        return matcher.match(url.path)
    except NotFound:
        return None, {}


def image_url_from_path(path):
    return urlparse.urljoin(current_app.config['IMAGE_CDN'], path)
