import re
import boto
import uuid
from jinja2 import Environment, PackageLoader
from rockpack.mainsite import app
from rockpack.mainsite.helpers.urls import url_for


# Pick title from a html string
TITLE_RE = re.compile('<title>([^<]+)</title>')

# Force https for static images in html email (seems to be needed by yahoo mail)
_assets_url = app.config.get('ASSETS_URL', '')
if _assets_url.startswith('//'):
    _assets_url = 'https:' + _assets_url
app.config['EMAIL_ASSETS_URL'] = _assets_url


def _tracker_client_id(email):
    # See https://developers.google.com/analytics/devguides/collection/protocol/v1/parameters#cid
    return uuid.uuid3(app.config['EMAIL_TRACKER_NS'], str(email))


env = Environment(loader=PackageLoader('rockpack.mainsite', app.config['EMAIL_TEMPLATE_PATH']))
env.globals.update(config=app.config, url_for=url_for, tracker_client_id=_tracker_client_id)


def send_email(recipient, body, subject=None, format='html'):
    if not subject:
        import HTMLParser
        subject = HTMLParser.HTMLParser().unescape(TITLE_RE.search(body).group(1))
    return boto.connect_ses().send_email(
        app.config['DEFAULT_EMAIL_SOURCE'],
        subject,
        body,
        [recipient],
        format=format
    )
