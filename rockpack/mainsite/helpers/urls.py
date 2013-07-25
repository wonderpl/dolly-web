import re
import urlparse
from unicodedata import normalize
from werkzeug.exceptions import NotFound
from flask import current_app, url_for as _url_for
from rockpack.mainsite import app

http_only_domains = []
if 'SERVER_NAME' in app.config:
    http_only_domains.append(app.config['SERVER_NAME'])
if 'SHARE_SUBDOMAIN' in app.config:
    http_only_domains.append(['.'.join(app.config['SHARE_SUBDOMAIN'], app.config['SERVER_NAME'])])


def url_for(*args, **kwargs):
    kwargs.setdefault('_external', True)
    url = _url_for(*args, **kwargs)
    # Ensure urls on secure domain use https:
    secure_subdomain = current_app.config.get('SECURE_SUBDOMAIN')
    if secure_subdomain and url.startswith('http://' + secure_subdomain + '.'):
        url = 'https://' + url[7:]
    # Ensure http-only domain don't get https protocol
    if any(url.startswith('https://' + domain + '/') for domain in http_only_domains if domain):
        url = 'http://' + url[8:]
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


# From http://flask.pocoo.org/snippets/5/
_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')


def slugify(text, delim=u'-'):
    """Generates an slightly worse ASCII-only slug."""
    result = []
    for word in _punct_re.split(text.lower()):
        word = normalize('NFKD', word).encode('ascii', 'ignore')
        if word:
            result.append(word)
    return unicode(delim.join(result))
