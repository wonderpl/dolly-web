from flask import json
from boto.sqs import connect_to_region
from boto.sqs.message import RawMessage
from rockpack.mainsite import app, init_app
from rockpack.mainsite.services.user.models import User


def _get_queue():
    global _queue
    if not _queue:
        conn = connect_to_region(app.config['SQS_REGION'])
        _queue = conn.get_queue(app.config['SQS_EMAIL_QUEUE'])
        _queue.set_message_class(RawMessage)
    return _queue
_queue = None


def process_sqs_message():
    message = _get_queue().read()
    if not message:
        return

    msg_body = json.loads(message.get_body())

    if (msg_body.get('Type') == 'Notification' and
            msg_body['TopicArn'].endswith('ses-notifications')):
        notification = json.loads(msg_body['Message'])

        if notification['notificationType'] == 'Bounce':
            bounce = notification['bounce']
            addresses = set(r['emailAddress'] for r in bounce['bouncedRecipients'])
            app.logger.info(
                'Recieved %s/%s bounce for %s',
                bounce['bounceType'], bounce['bounceSubType'], ', '.join(addresses))
            if bounce['bounceType'] == 'Permanent':
                for user in User.query.filter(User.email.in_(addresses)):
                    user.set_flag('bouncing')
                    user.save()
            message.delete()

        if notification['notificationType'] == 'Complaint':
            complaint = notification['complaint']
            addresses = set(r['emailAddress'] for r in complaint['complainedRecipients'])
            app.logger.warning(
                'Recieved %s complaint for %s',
                complaint.get('complaintFeedbackType', 'unknown'), ', '.join(addresses))
            message.delete()


if __name__ == '__main__':
    # uwsgi mule will execute here

    if not app.blueprints:
        init_app()
        # Needed to generate urls (for ES signals)
        app.app_context().push()

    if 'SENTRY_DSN' in app.config:
        from raven.contrib.flask import Sentry
        Sentry(app, logging=app.config.get('SENTRY_ENABLE_LOGGING'))

    while True:
        process_sqs_message()
