from pyes import ES
from rockpack.mainsite import app


es_url = app.config.get('ELASTICSEARCH_URL')


def get_es_connection():
    """ Connection handler for elastic search """
    if not es_url:
        return None
    return ES(es_url)


es_connection = get_es_connection()
