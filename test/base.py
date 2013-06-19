import time
import uuid
import unittest
import rockpack
import pytest
from datetime import date
from rockpack.mainsite.core.dbapi import db
from rockpack.mainsite.services.user.models import User


class RockPackTestCase(unittest.TestCase):

    set_trace = pytest.set_trace

    def setUp(self):
        self.app = rockpack.mainsite.app
        self.session = db.session

    def create_test_user(self, **kwargs):
        postfix = uuid.uuid4().hex
        user = dict(
            username='test_' + postfix,
            password='password',
            first_name='foo',
            last_name='bar',
            date_of_birth=date(2000, 1, 1),
            email='test_' + postfix + '@test.rockpack.com',
            avatar='',
            refresh_token='',
            is_active=True,
            locale='en-us',
        )
        user.update(kwargs)
        return User.create_with_channel(**user)

    def wait_for_es(self):
        if self.app.config.get('ELASTICSEARCH_URL'):
            time.sleep(2)
