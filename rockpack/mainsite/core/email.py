import re
import boto
from jinja2 import Environment, PackageLoader
from rockpack.mainsite import app
from rockpack.mainsite.helpers.urls import url_for


# Pick title from a html string
TITLE_RE = re.compile('<title>([^<]+)</title>')


env = Environment(loader=PackageLoader('rockpack.mainsite', app.config['EMAIL_TEMPLATE_PATH']))
env.globals.update(config=app.config, url_for=url_for)


def send_email(recipient, body, subject=None, format='html'):
    if not subject:
        subject = TITLE_RE.search(body).group(1)
    return boto.connect_ses().send_email(
        app.config['DEFAULT_EMAIL_SOURCE'],
        subject,
        body,
        [recipient],
        format=format
    )
