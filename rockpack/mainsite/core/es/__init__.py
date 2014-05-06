import pyes
import time
from flask import request
from rockpack.mainsite import app
from rockpack.mainsite.core import timing


es_url = app.config.get('ELASTICSEARCH_URL')

if es_url:
    try:
        from pyes.connection_http import update_connection_pool
    except ImportError:
        # not available in earlier pyes versions
        pass
    else:
        update_connection_pool(app.config.get('ELASTICSEARCH_CONNECTION_POOL_MAXSIZE', 4))


class LoggingListBulker(pyes.models.ListBulker):
    def __init__(self, *args, **kwargs):
        self.flush_count = 0
        self.flush_timer = None
        super(LoggingListBulker, self).__init__(*args, **kwargs)

    def initialise_timer(self):
        self.flush_timer = time.time()

    def unset_timer(self):
        self.flush_timer = None

    def metric(self, name):
        return '.'.join([self.__class__.__module__,
                         self.__class__.__name__,
                         name])

    def log_flushes(self):
        timing.record_counter(self.metric('count'), self.flush_count)

    def log_timer(self):
        timing.record_counter(self.metric('elapsed_time'),
                              time.time() - self.flush_timer)

    def flush_bulk(self, forced=False):
        """ Counts any flushes made and logs the count
            once a forced flush is called.

            Forced flushes are required as the bulkers
            __del__ method isn't guaranteed to be called
            so there may be unflushed data still present """

        if self.flush_timer is None:
            self.initialise_timer()

        if len(self.bulk_data) >= self.bulk_size or forced:
            self.flush_count += 1

        result = super(LoggingListBulker, self).flush_bulk(forced=forced)
        if forced:
            self.log_flushes()
            self.log_timer()
            self.flush_count = 0
            self.flush_timer = None
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


# Monkey patch reindex capability on to the ES()
pyes.ES.reindex = pyes_reindex
es_connection = get_es_connection()
