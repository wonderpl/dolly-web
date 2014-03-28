import logging
import pyes
import time
import datetime
from flask import json
from rockpack.mainsite import app
from rockpack.mainsite.core.es import get_es_connection
from rockpack.mainsite.core.es import api
from rockpack.mainsite.core.es import exceptions


logger = logging.getLogger(__name__)


class Aliasing(object):

    conn = get_es_connection(timeout=None)

    def __init__(self, doc_type):
        self.doc_type = doc_type

        # Get the current index alias name for the real index e.g. rockpack, dolly
        self.alias = api.ESObjectIndexer.get_alias(doc_type)

        # Get the mapping for the doc_type in question
        self.mapping = api.ESObjectIndexer.get_mapping(doc_type)

        self.settings = api.ESObjectIndexer.get_settings(doc_type)

        self.index_prefix = self.get_base_index_prefix(self.alias)

    @classmethod
    def get_base_index_prefix(cls, alias):
        """ Base index prefix is just the current index alias """
        doc_type = next(iter([key for key, a in api.ESObjectIndexer.aliases.items() if a == alias]))
        return api.ESObjectIndexer.get_index(doc_type)

    @classmethod
    def get_base_indices_for(cls, alias):
        """ Get all the indices assigned to `alias` """
        try:
            indices = cls.conn.get_alias(alias)
        except pyes.exceptions.IndexMissingException:
            raise exceptions.IndexMissing("No indices for alias '%s'" % alias)
        else:
            return indices

    @classmethod
    def get_current_index(cls, alias):
        """ From the indices returned for the current `alias`,
            find all the ones that match the prefix (again, we
            should just find one) """

        def func(x, y):
            return x if int(x.split('_')[2]) > int(y.split('_')[2]) else y

        indices = cls.get_base_indices_for(alias)
        prefix = cls.get_base_index_prefix(alias)
        existing_indices = [i for i in indices if i.startswith(prefix)]

        if not existing_indices:
            raise exceptions.ExpectedIndex("No indices matching prefix '%s' found for alias '%s'" % (prefix, alias))
        elif len(existing_indices) == 0:
            return existing_indices[0]
        else:
            return reduce(func, existing_indices)

    @classmethod
    def integrity_check(cls, source_index, target_index, doc_type, margin=100):
        """ Check count in target index is the same as source index
            within a margin of error specified by `margin` """
        all_query = {"match_all": {}}
        time.sleep(2)
        source_count = cls.conn.count(all_query, source_index, doc_type).count
        target_count = cls.conn.count(all_query, target_index, doc_type).count

        app.logger.debug("Integrity check: %d of %d", target_count, source_count)
        if (margin * -1) < (source_count - target_count) < margin:
            return True

        raise exceptions.IntegrityError(
            "Counts (%d/%d) outside error bounds" % (target_count, source_count))

    @classmethod
    def generate_new_index_name(cls, prefix):
        """ Builds a name from the current time
            in seconds since epoch and the index prefix
            e.g. rockpack_channel_1385124160 """

        timestamp = datetime.datetime.utcnow().strftime("%s")
        return '%s_%s' % (prefix, timestamp)

    @classmethod
    def reindex(cls, source_index, source_type, target_index, target_type, with_version=False):
        """ Takes a source index/type and reindexes to a target source/type """
        reindex_query = {"query": {"match_all": {}}}
        reindex_list = [target_index, target_type, source_index, source_type]
        app.logger.info('Re-indexing %s/%s to %s/%s', *reindex_list)
        cls.conn.reindex(*([json.dumps(reindex_query)] + reindex_list), with_version=with_version)

    @classmethod
    def assign(cls, alias, target_index):
        add_command = ('add', target_index, alias, {})
        cls.conn.change_aliases([add_command])

    @classmethod
    def reassign(cls, alias, source_index, target_index):
        """ Takes a source index and reassigns the
            associated alias to the target index (add/delete op) """
        app.logger.info('Re-assigning alias to new index')
        add_command = ('add', target_index, alias, {})
        remove_command = ('remove', source_index, alias, {})
        cls.conn.change_aliases([add_command, remove_command])

    @classmethod
    def delete_index(cls, index):
        cls.conn.delete_index(index)

    def current_index(self):
        return self.get_current_index(self.alias)

    def create_new_index(self):
        index_name = self.generate_new_index_name(self.index_prefix)
        self.conn.indices.create_index(index_name, settings=self.settings)
        self.conn.put_mapping(doc_type=self.doc_type, mapping=self.mapping, indices=[index_name])
        return index_name

    def reindex_to(self, target, with_version=False):
        """ Helper method to reindex `self.doc_type`from the
            existing index info stored with `self` in to a new index. """

        self.reindex(self.get_current_index(self.alias), self.doc_type,
                     target, self.doc_type, with_version=with_version)

    def reassign_to(self, target):
        self.reassign(self.alias, self.get_current_index(self.alias), target)
