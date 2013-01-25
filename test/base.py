import unittest
import rockpack
import pytest


class RockPackTestCase(unittest.TestCase):

    set_trace = pytest.set_trace

    def setUp(self):
        rockpack.mainsite.app.config['TESTING'] = True
        self.client = rockpack.mainsite.app.test_client()
        self.app = self.client.application
        self.session = rockpack.mainsite.core.dbapi.session
