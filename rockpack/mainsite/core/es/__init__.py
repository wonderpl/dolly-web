from flask import request
from pyes import ES
from pyes import utils
from rockpack.mainsite import app


def _partial_update(self, index, doc_type, id, script, params=None,
                   upsert=None, querystring_args=None):
    """
    Partially update a document with a script
    """
    if querystring_args is None:
        querystring_args = {}

    cmd = {"script": script}

    if params:
        cmd["params"] = params

    if upsert:
        cmd["upsert"] = upsert

    path = utils.make_path([index, doc_type, id, "_update"])
    return self._send_request('POST', path, cmd, querystring_args)

ES.partial_update = _partial_update


es_url = app.config.get('ELASTICSEARCH_URL')


def use_elasticsearch():
    return es_url and request.args.get('_es') != 'false'


def get_es_connection():
    """ Connection handler for elastic search """
    if not es_url:
        return None
    return ES(es_url)


es_connection = get_es_connection()
