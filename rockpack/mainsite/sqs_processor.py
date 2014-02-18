import os
import time
import logging
from boto.sqs import connect_to_region
from boto.sqs.jsonmessage import JSONMessage
from rockpack.mainsite import app, init_app


class SqsProcessor(object):

    sqs_visibility_timeout = app.config.get('SQS_DEFAULT_VISIBILITY_TIMEOUT', 600)
    message_class = JSONMessage

    # _queue is a class property shared between all instances
    _queue = None

    @classmethod
    def getqueue(cls):
        if not cls._queue:
            conn = connect_to_region(app.config['SQS_REGION'])
            cls._queue = conn.get_queue(cls.queue_name)
            if not cls._queue:
                raise Exception('Unable to access queue: %s' % cls.queue_name)
            cls._queue.set_message_class(cls.message_class)
        return cls._queue

    @classmethod
    def write_message(cls, message, delay_seconds=None):
        cls.getqueue().write(cls.message_class(body=message), delay_seconds)

    def process_message(self, message):
        pass

    def poll(self):
        message = self.getqueue().read(self.sqs_visibility_timeout)
        if not message:
            return
        if self.process_message(message.get_body()) is not False:
            # Delete only on success
            message.delete()

    def run(self):
        # uwsgi mule will execute here
        if not app.blueprints:
            init_app()

        if 'SENTRY_DSN' in app.config:
            from raven.contrib.flask import Sentry
            Sentry(app, logging=app.config.get('SENTRY_ENABLE_LOGGING'), level=logging.WARN)

        while True:
            if os.path.exists('/tmp/sqs-%s.lock' % self.queue_name):
                time.sleep(10)
            else:
                with app.app_context():
                    self.poll()
