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
        userdata = dict(
            username='test_' + postfix,
            password='password',
            first_name='Alexia',
            last_name='Barrichello',
            date_of_birth=date(2000, 1, 1),
            email='test_' + postfix + '@test.rockpack.com',
            avatar='',
            refresh_token='',
            is_active=True,
            locale='en-us',
        )
        userdata.update(kwargs)
        user = User.create_with_channel(**userdata)
        self.session.commit()
        return user

    def wait_for_es(self):
        if self.app.config.get('ELASTICSEARCH_URL'):
            time.sleep(2)
