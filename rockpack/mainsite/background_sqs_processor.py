from functools import wraps
from rockpack.mainsite import app
from rockpack.mainsite.sqs_processor import SqsProcessor


class BackgroundSqsProcessor(SqsProcessor):

    queue_name = app.config['SQS_BACKGROUND_QUEUE']

    def process_message(self, message):
        try:
            module = __import__(message['module'], fromlist=True)
            func = getattr(module, message['function'])
        except (ImportError, AttributeError):
            app.logger.error('Unable to parse background message: %s', message)

        # Don't use background_on_sqs wrapper again
        func = getattr(func, '_orig_func', func)

        try:
            func(*message['args'], **message['kwargs'])
        except Exception:
            app.logger.exception('Unable to run background function %s', message['function'])
            return False
        else:
            app.logger.debug('Ran background function %s', message['function'])


def background_on_sqs(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        call = dict(
            module=func.__module__,
            function=func.__name__,
            args=args,
            kwargs=kwargs,
        )
        BackgroundSqsProcessor.write_message(call)
    wrapper._orig_func = func
    return wrapper


if __name__ == '__main__':
    BackgroundSqsProcessor().run()
