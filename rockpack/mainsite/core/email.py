import boto
from jinja2 import Environment, PackageLoader
from rockpack.mainsite import app
from rockpack.mainsite.helpers.urls import url_for


env = Environment(loader=PackageLoader('rockpack.mainsite', 'static/assets/emails'))
env.globals.update(config=app.config, url_for=url_for)


def send_email(recipient, subject, body, format="text"):
    return boto.connect_ses().send_email(
        app.config['DEFAULT_EMAIL_SOURCE'],
        subject,
        body,
        [recipient],
        format=format
    )
