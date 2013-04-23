import unittest
import rockpack
import pytest
import uuid
from datetime import date
from rockpack.mainsite.core.es import mappings
from rockpack.mainsite.core.es import helpers
from rockpack.mainsite.core.dbapi import db
from rockpack.mainsite.services.user.models import User


class RockPackTestCase(unittest.TestCase):

    set_trace = pytest.set_trace

    def setUp(self):
        self.app = rockpack.mainsite.app
        self.session = db.session

        if self.app.config.get('ELASTICSEARCH_URL'):
            self._channel_index = mappings.CHANNEL_INDEX = uuid.uuid4().hex
            self._video_index = mappings.VIDEO_INDEX = uuid.uuid4().hex
            self._user_index = mappings.USER_INDEX = uuid.uuid4().hex

            i = helpers.Indexing()
            i.create_all_indexes(rebuild=True)
            i.create_all_mappings()

            i = helpers.DBImport()
            i.import_channels()
            i.import_videos()
            i.import_owners()

    def tearDown(self):
        if self.app.config.get('ELASTICSEARCH_URL'):
            i = helpers.Indexing()
            i.delete_index('channel')
            i.delete_index('video')
            i.delete_index('user')

    def create_test_user(self):
        postfix = uuid.uuid4().hex
        return User(
            username='test_' + postfix,
            password_hash='',
            first_name='foo',
            last_name='bar',
            date_of_birth=date(2000, 1, 1),
            email='test_' + postfix + '@test.rockpack.com',
            avatar='',
            refresh_token='',
            is_active=True,
        ).save()
