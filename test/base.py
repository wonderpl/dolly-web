import unittest
import rockpack
import pytest
import uuid
from datetime import date
from werkzeug.security import generate_password_hash
from rockpack.mainsite.core.dbapi import db
from rockpack.mainsite.services.user.models import User


class RockPackTestCase(unittest.TestCase):

    set_trace = pytest.set_trace

    def setUp(self):
        self.app = rockpack.mainsite.app
        self.session = db.session

    def create_test_user(self):
        postfix = uuid.uuid4().hex
        password_hash = generate_password_hash('password')
        return User(
            username='test_' + postfix,
            password_hash=password_hash,
            first_name='foo',
            last_name='bar',
            date_of_birth=date(2000, 1, 1),
            email='test_' + postfix + '@test.rockpack.com',
            avatar='',
            refresh_token='',
            is_active=True,
            locale='en-us',
        ).save()
