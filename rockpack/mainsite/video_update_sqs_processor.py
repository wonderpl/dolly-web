from boto.sqs import connect_to_region
from boto.sqs.jsonmessage import JSONMessage
from rockpack.mainsite import app, init_app
from rockpack.mainsite.core.es.api import es_update_channel_videos


def _get_queue():
    global _queue
    if not _queue:
        conn = connect_to_region(app.config['SQS_REGION'])
        _queue = conn.get_queue(app.config['SQS_VIDEO_UPDATE_QUEUE'])
        _queue.set_message_class(JSONMessage)
    return _queue
_queue = None


def _write_message(msg):
    _get_queue().write(JSONMessage(body=msg), None)


def process_sqs_message():
    message = _get_queue().read()
    if not message:
        return

    # Parse message
    updates = message.get_body()
    try:
        es_update_channel_videos(updates['extant'], updates['deleted'], async=False)
    except Exception, e:
        app.logger.exception('Failed to update channel videos: %s with %s', updates, str(e))
        # message will re-appear on the queue after visibility timeout
        return

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
