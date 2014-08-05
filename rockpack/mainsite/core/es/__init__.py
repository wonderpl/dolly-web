import os
import time
import pyes
from flask import request
from wonder.common import timing
from rockpack.mainsite import app


es_url = app.config.get('ELASTICSEARCH_URL')

if es_url:
    try:
        from pyes.connection_http import update_connection_pool
    except ImportError:
        # not available in earlier pyes versions
        pass
    else:
        update_connection_pool(app.config.get('ELASTICSEARCH_CONNECTION_POOL_MAXSIZE', 4))


class FlushTimer(object):

    class UnstartedTimerError(Exception):
        pass

    __shared_state = {}

    def __init__(self):
        self.__dict__ = self.__shared_state
        self.start_time = None
        self.elapsed = 0

    def start(self):
        if self.start_time is None:
            self.elapsed = 0
            self.start_time = time.time()

    def stop(self):
        try:
            self.elapsed = time.time() - self.start_time
        except TypeError:
            raise FlushTimer.UnstartedTimerError('Cannot stop an unstarted timer')
        else:
            self.start_time = None
            return self.elapsed


class LoggingListBulker(pyes.models.ListBulker):
    def __init__(self, *args, **kwargs):
        self.flush_count = 0
        self.data_size = 0
        self.flush_timer = FlushTimer()
        super(LoggingListBulker, self).__init__(*args, **kwargs)

    def metric(self, name):
        return 'es.listbulker.' + name

    def log_flush_count(self):
        timing.record_counter(self.metric('flush_count_per_forced'), self.flush_count, gauge=True)

    def log_bulk_size(self):
        timing.record_counter(self.metric('bulk_size'), self.data_size, gauge=True)

    def log_timer(self):
        timing.record_timing(self.metric('elapsed_time'), self.flush_timer.elapsed)

    def inc_flush_count(self):
        self.flush_count += 1

    def reset_flush_count(self):
        self.flush_count = 0

    def flush_bulk(self, forced=False):
        """ Counts any flushes made and logs the count
            once a forced flush is called.

            Forced flushes are required as the bulkers
            __del__ method isn't guaranteed to be called
            so there may be unflushed data still present """

        self.flush_timer.start()

        self.data_size = len(self.bulk_data)

        if len(self.bulk_data) >= self.bulk_size or forced:
            self.log_bulk_size()
            self.inc_flush_count()

        result = super(LoggingListBulker, self).flush_bulk(forced=forced)
        if forced:
            self.flush_timer.stop()
            self.log_timer()
            self.log_flush_count()
            self.reset_flush_count()
        return result


def pyes_reindex(self, doc, index, doc_type, search_index, search_type, with_version=False):
    """ Requires https://github.com/karussell/elasticsearch-reindex installed
        on instance where the target command is to be run

        Reindexes an index from another index ie. get data from
        http://localhost:9200/search_index/search_type/ and insert data in to this index"""

    query_params = dict(searchIndex=search_index,
                        searchType=search_type,
                        withVersion=with_version)

    path = pyes.utils.make_path(index, doc_type, '_reindex')
    try:
        return self._send_request('PUT', path, doc, params=query_params)
    except pyes.exceptions.ElasticSearchException:
        # Ignore this - pyes doesn't like that ES returns '' on a 200
        pass


def use_elasticsearch():
    return es_url and not (request and request.args.get('_es') == 'false')


def get_es_connection(timeout=app.config.get('ELASTICSEARCH_TIMEOUT', 60)):
    """ Connection handler for elastic search """
    if not es_url:
        return None
    return pyes.ES(es_url, timeout=timeout, bulker_class=LoggingListBulker)


def discover_cluster_nodes(prefix='es'):
    if not es_connection:
        return
    new_servers = []
    for node in es_connection.cluster_nodes()['nodes'].values():
        if node['name'].startswith(prefix):
            server = node['http_address'].replace("]", "").replace("inet[", "http:/")
            new_servers.append(server)
    if new_servers:
        app.logger.info('Setting ES servers for process %d: %s',
                        os.getpid(), ', '.join(new_servers))
        es_connection.servers = new_servers
        es_connection._check_servers()
        es_connection._init_connection()
        pyes.connection_http.POOL_MANAGER.clear()
    else:
        app.logger.warning('No additional ES servers found for process %d',
                           os.getpid())


# Monkey patch reindex capability on to the ES()
pyes.ES.reindex = pyes_reindex
es_connection = get_es_connection()
