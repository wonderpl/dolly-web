import unittest
import rockpack


class RockPackTestCase(unittest.TestCase):

    def setUp(self):
        rockpack.mainsite.app.config['TESTING'] = True
        self.client = rockpack.mainsite.app.test_client()
        self.app = self.client.application
        self.session = rockpack.mainsite.core.dbapi.session
