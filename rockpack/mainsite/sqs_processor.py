import os
import sys
import time
import signal
import logging
from boto.sqs import connect_to_region
from boto.sqs.jsonmessage import JSONMessage
from rockpack.mainsite import app, init_app
from rockpack.mainsite.core.es import discover_cluster_nodes


def hup_handler(sighup, frame):
    global _hup_received
    _hup_received = True
_hup_received = False


class MuleRunner(object):

    lock_file = None
    sleep_interval = None

    def setup(self):
        # uwsgi mule will execute here
        if not app.blueprints:
            init_app()

        # Catch HUP from uwsgi
        signal.signal(signal.SIGHUP, hup_handler)

        if 'SENTRY_DSN' in app.config:
            from raven.contrib.flask import Sentry
            Sentry(app, logging=app.config.get('SENTRY_ENABLE_LOGGING'), level=logging.WARN)

        # Use ES cluster nodes directly for batch jobs
        discover_cluster_nodes()

    def run(self):
        self.setup()

        while True:
            if self.lock_file and os.path.exists(self.lock_file):
                time.sleep(10)
            else:
                with app.app_context():
                    success = self.poll()
                if self.sleep_interval and not success and not _hup_received:
                    time.sleep(self.sleep_interval)
            if _hup_received:
                sys.exit()


class SqsProcessor(MuleRunner):

    sqs_visibility_timeout = app.config.get('SQS_DEFAULT_VISIBILITY_TIMEOUT', 600)
    message_class = JSONMessage

    queue_name = None

    # _queue is a class property shared between all instances
    _queue = None

    def __init__(self):
        if self.queue_name:
            self.lock_file = '/tmp/sqs-%s.lock' % self.queue_name

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
