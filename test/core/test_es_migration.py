import time
import unittest
import datetime
import pyes
import pytest
from mock import patch
from rockpack.mainsite.core.es import migration, use_elasticsearch


PATCH_ALIAS = PATCH_INDEX_PREFIX = 'test_index'


@pytest.mark.skipif(not use_elasticsearch(), reason="requires elasticsearch")
class MigrationTestCase(unittest.TestCase):

    def setUp(self):
        self.new_index = None
        self.aliasing = migration.Aliasing('channel')

        # override settings
        self.aliasing.alias = PATCH_ALIAS
        self.aliasing.mapping = {
            "properties": {
                "title": {
                    "type": "string",
                    "index": "not_analyzed"
                }
            }
        }
        self.aliasing.index_prefix = PATCH_INDEX_PREFIX

        self.index_names = []

    def tearDown(self):
        for index in self.index_names:
            try:
                self.aliasing.conn.delete_index(index)
            except:
                pass

    def _new_index(self):
        """ Create a new index and return the name.
            Index name is stored in a list for deletion
            at the end of the test run """
        i = self.aliasing.create_new_index()
        self.index_names.append(i)
        return i

    @patch('rockpack.mainsite.core.es.api.ESObjectIndexer.aliases', dict(test=PATCH_ALIAS))
    @patch('rockpack.mainsite.core.es.api.ESObjectIndexer.get_index')
    def test_create_index(self, get_index):
        # ensure we can get the correct alias in calls
        get_index.return_value = PATCH_ALIAS

        # create index
        new_index = self._new_index()

        # assert the 3rd component starts with today
        assert new_index.split('_')[2].startswith(datetime.datetime.utcnow().strftime("%s")[:-4])

        # assign an alias
        self.aliasing.assign(self.aliasing.alias, new_index)

        # lookup the new current index and check the name matches
        self.assertEquals(new_index, self.aliasing.current_index())

        # insert some data for the swap
        doc = {"title": "this is a test"}
        self.aliasing.conn.index(doc, self.aliasing.alias, self.aliasing.doc_type, id=1)

        # reindex to new index and swap alias
        time.sleep(2)
        newer_index = self._new_index()
        time.sleep(1)
        self.aliasing.reindex_to(newer_index)
        self.aliasing.reassign_to(newer_index)

        # check the data is in the index
        time.sleep(1)
        result = list(
            self.aliasing.conn.search(
                pyes.MatchAllQuery(),
                indices=newer_index,
                doc_types=self.aliasing.doc_type)
        )
        self.assertEquals(len(result), 1)
        self.assertEquals(result[0].title, doc['title'])

        # and now via the alias after we delete the old index
        time.sleep(1)
        self.aliasing.conn.delete_index(new_index)
        result = list(
            self.aliasing.conn.search(
                pyes.MatchAllQuery(),
                indices=self.aliasing.alias,
                doc_types=self.aliasing.doc_type)
        )
        self.assertEquals(len(result), 1)
        self.assertEquals(result[0].title, doc['title'])

        for index in self.aliasing.get_base_indices_for(self.aliasing.alias):
            self.assertIn(index, [new_index, newer_index])
