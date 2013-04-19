from pyes import ES
from rockpack.mainsite import app


def get_es_connection():
    """ Connection handler for elastic search """
    if not app.config.get('ELASTICSEARCH_URL'):
        return None
    return ES(app.config.get('ELASTICSEARCH_URL'))
