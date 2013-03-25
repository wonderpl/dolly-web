from pyes import ES
from rockpack.mainsite import app


def get_es_connection():
    """ Connection handler for elastic search """
    return ES(app.config.get('ELASTICSEARCH_URL'))
