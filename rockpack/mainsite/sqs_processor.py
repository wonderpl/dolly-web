from datetime import datetime, timedelta
from boto.sqs import connect_to_region
from boto.sqs.jsonmessage import JSONMessage
from rockpack.mainsite import app, init_app
from rockpack.mainsite.manager import manager


SQS_DELAY_LIMIT = 900


def _get_queue():
    global _queue
    if not _queue:
        conn = connect_to_region(app.config['SQS_REGION'])
        _queue = conn.get_queue(app.config['SQS_CRON_QUEUE'])
        _queue.set_message_class(JSONMessage)
    return _queue
_queue = None


def _write_message(command, next_run, delay_seconds=None):
    body = dict(command=command, next_run=next_run.isoformat())
    if delay_seconds is not None:
        delay_seconds = min(SQS_DELAY_LIMIT, delay_seconds)
    _get_queue().write(JSONMessage(body=body), delay_seconds)


def process_sqs_message():
    message = _get_queue().read()
    if not message:
        return

    # Parse message
    body = message.get_body()
    commands = manager.get_cron_commands()
    try:
        command = body['command']
        next_run = datetime.strptime(body['next_run'][:19], '%Y-%m-%dT%H:%M:%S')
        interval = commands[command]
    except Exception:
        app.logger.exception('Failed to parse message: %r', body)
        # leave message on queue
        return

    # Check if it's time to run this command now.  Adding 10s leeway so that messages
    # that appear after delay_seconds and close to next_run don't get postponed.
    delta = (next_run - datetime.utcnow()).total_seconds()
    if delta > 10:
        # Need to wait a bit longer until next_run
        _write_message(command, next_run, delta)
        message.delete()
        return

    try:
        manager.handle('cron', command)
    except Exception:
        app.logger.exception('Failed to run command: %s', command)
        # message will re-appear on the queue after visibility timeout
        return

    _write_message(command, datetime.utcnow() + timedelta(seconds=interval), interval)
    message.delete()


def init_messages(commands):
    for command in manager.get_cron_commands():
        if not commands or command in commands:
            _write_message(command, datetime.utcnow())


if __name__ == '__main__':
    # uwsgi mule will execute here

    if not app.blueprints:
        init_app()

    if 'SENTRY_DSN' in app.config:
        from raven.contrib.flask import Sentry
        Sentry(app, logging=app.config.get('SENTRY_ENABLE_LOGGING'))

    while True:
        process_sqs_message()
