import boto
from jinja2 import Environment, PackageLoader
from rockpack.mainsite import app

env = Environment(loader=PackageLoader('rockpack.mainsite', 'static/assets/emails'))


def send_email(recipient, subject, body, format="text"):
    return boto.connect_ses().send_email(
        app.config['DEFAULT_EMAIL_SOURCE'],
        subject,
        body,
        [recipient],
        format=format
    )
