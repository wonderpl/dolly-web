from functools import wraps
from flask import g
from rockpack.mainsite import app
from rockpack.mainsite.sqs_processor import SqsProcessor


def _run_call(message):
    try:
        module = __import__(message['module'], fromlist=True)
        func = getattr(module, message['function'])
    except (ImportError, AttributeError):
        app.logger.error('Unable to parse background message: %s', message)
        return False

    # Don't use background_on_sqs wrapper again
    func = getattr(func, '_orig_func', func)

    try:
        func(*message['args'], **message['kwargs'])
    except Exception:
        app.logger.exception('Unable to run background function %s', message['function'])
        return False
    #else:
    #    app.logger.debug('Ran background function %s', message['function'])


@app.teardown_request
def _run_later(exception):
    if not exception:
        for call in getattr(g, '_background_on_sqs', []):
            _run_call(call)
    g._background_on_sqs = []


class BackgroundSqsProcessor(SqsProcessor):

    queue_name = app.config['SQS_BACKGROUND_QUEUE']
    sqs_visibility_timeout = app.config.get('SQS_BACKGROUND_VISIBILITY_TIMEOUT', 1200)

    def process_message(self, message):
        return _run_call(message)


def background_on_sqs(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        call = dict(
            module=func.__module__,
            function=func.__name__,
            args=args,
            kwargs=kwargs,
        )
        if BackgroundSqsProcessor.queue_name:
            BackgroundSqsProcessor.write_message(call)
        else:
            # put the call on the request context for _run_later
            if not hasattr(g, '_background_on_sqs'):
                g._background_on_sqs = []
            g._background_on_sqs.append(call)
    wrapper._orig_func = func
    return wrapper


if __name__ == '__main__':
    BackgroundSqsProcessor().run()
