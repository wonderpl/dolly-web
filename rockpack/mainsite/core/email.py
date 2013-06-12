import boto
from rockpack.mainsite import app


def send_email(recipient, subject, body, format="text"):
    return boto.connect_ses().send_email(
        app.config['DEFAULT_EMAIL_SOURCE'],
        subject,
        body,
        [recipient],
        format=format
    )
