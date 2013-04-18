import time
import logging
from functools import wraps
from flask import request, json
from sqlalchemy.interfaces import ConnectionProxy
import requests.api


statsd_client = None
log = logging.getLogger(__name__)


def record_timing(name, value):
    if statsd_client:
        statsd_client.timing(name, value * 1000)
    else:
        log.info('%s: %dms', name, value * 1000)


def record_counter(name, value):
    if statsd_client:
        statsd_client.update_stats(name, value)
    else:
        log.info('%s: %d', name, value)


def wrap(f, prefix=''):
    @wraps(f)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = f(*args, **kwargs)
        timing = getattr(request, '_timing', None)
        if timing:
            timing.setdefault(prefix + f.__name__, []).append(time.time() - start)
        return result
    return wrapper


def before_request():
    request._timing = dict(_start_request=time.time())


def after_request(response):
    timing = getattr(request, '_timing', None)
    if timing:
        response_time = time.time() - timing.pop('_start_request')
        metric = lambda n: '.'.join(('views', request.endpoint, n))
        record_timing(metric('response_time'), response_time)
        for name, times in timing.items():
            record_timing(metric(name + '_time'), sum(times))
            record_counter(metric(name + '_count'), len(times))
    return response


def setup_timing(app):
    global statsd_client
    statsd_host = app.config.get('STATSD_HOST')
    if statsd_host:
        import pystatsd
        statsd_client = pystatsd.Client(host=statsd_host, prefix=app.name)

    if app.config.get('ENABLE_TIMINGS'):
        json.loads = wrap(json.loads, 'json.')
        json.dumps = wrap(json.dumps, 'json.')
        ConnectionProxy.execute = wrap(ConnectionProxy.execute, 'db.')
        requests.api.request = wrap(requests.api.request, 'requests.')
        app.before_request(before_request)
        app.after_request(after_request)
