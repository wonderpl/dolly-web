from flask import request
from pyes import ES
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


def use_elasticsearch():
    return es_url and request.args.get('_es') != 'false'


def get_es_connection():
    """ Connection handler for elastic search """
    if not es_url:
        return None
    return ES(es_url)


es_connection = get_es_connection()
