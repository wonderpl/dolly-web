from flask import json
from boto.sqs.message import RawMessage
from rockpack.mainsite import app
from rockpack.mainsite.services.user.models import User
from rockpack.mainsite.sqs_processor import SqsProcessor


class EmailSqsProcessor(SqsProcessor):

    queue_name = app.config['SQS_EMAIL_QUEUE']
    message_class = RawMessage

    def process_message(self, message):
        msg_body = json.loads(message)

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

            elif notification['notificationType'] == 'Complaint':
                complaint = notification['complaint']
                addresses = set(r['emailAddress'] for r in complaint['complainedRecipients'])
                app.logger.warning(
                    'Recieved %s complaint for %s',
                    complaint.get('complaintFeedbackType', 'unknown'), ', '.join(addresses))


if __name__ == '__main__':
    EmailSqsProcessor().run()
