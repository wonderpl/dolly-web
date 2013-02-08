import unittest
import rockpack
import pytest
from rockpack.mainsite.core.dbapi import db


class RockPackTestCase(unittest.TestCase):

    set_trace = pytest.set_trace

    def setUp(self):
        self.app = rockpack.mainsite.app
        self.session = db.session
