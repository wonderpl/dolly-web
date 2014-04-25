import time
import urllib
import urllib3
import logging
import requests
from functools import wraps
from flask import request, json
from sqlalchemy.engine.base import Connection


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


def request_timing():
    try:
        return request._timing
    except Exception:
        pass


def wrap(f, prefix='', is_view=True):
    @wraps(f)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = f(*args, **kwargs)
        runtime = time.time() - start
        if callable(prefix):
            key = prefix(f, *args, **kwargs)
        else:
            key = prefix + f.__name__
        if is_view:
            timing = request_timing()
            if timing:
                timing.setdefault(key, []).append(runtime)
        else:
            record_timing(key + '.run_time', runtime)
        return result
    return wrapper


def before_request():
    request._timing = dict(_start_request=time.time())


def after_request(response):
    timing = request_timing()
    if timing and request.endpoint:
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
        urllib.urlopen = wrap(urllib.urlopen, 'urllib.')
        urllib3.connectionpool.HTTPConnectionPool.urlopen = wrap(urllib3.connectionpool.HTTPConnectionPool.urlopen, 'urllib3.')
        json.loads = wrap(json.loads, 'json.')
        json.dumps = wrap(json.dumps, 'json.')
        Connection.execute = wrap(Connection.execute, 'db.')
        requests.api.request = wrap(requests.api.request, 'requests.')
        if app.config.get('USE_GEVENT'):
            requests.Session.request = wrap(requests.Session.request, 'requests.')
            from geventhttpclient.client import HTTPClient
            HTTPClient.request = wrap(HTTPClient.request, 'requests.')
        from rockpack.mainsite.sqs_processor import SqsProcessor
        SqsProcessor.write_message = classmethod(wrap(
            SqsProcessor.write_message.__func__, _sqs_processor_prefix, False))
        app.before_request(before_request)
        app.after_request(after_request)


def _sqs_processor_prefix(f, *args, **kwargs):
    cls, msg, delay = args
    try:
        cmd = msg['command']
    except Exception:
        cmd = None
    return '.'.join(filter(None, (cls.__name__, f.__name__, cmd)))
