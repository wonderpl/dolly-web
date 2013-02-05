import unittest
import rockpack
import pytest
from fixture import DataTestCase
from rockpack.mainsite.core.dbapi import db


# patch for sqlalchemy and SessionMaker

from flask.ext.sqlalchemy import _SignalTrackingMapperExtension, orm
from sqlalchemy.orm.interfaces import EXT_CONTINUE


def _record(self, mapper, model, operation):
    pk = tuple(mapper.primary_key_from_instance(model))
    # Some hack just to prevent from crashing when trying to look
    # for _model_changes attribute. Happens when loading fixutres with
    # the fixture library.
    if not hasattr(orm.object_session(model), '_model_changes'):
        orm.object_session(model)._model_changes = dict()
    orm.object_session(model)._model_changes[pk] = (model, operation)
    return EXT_CONTINUE


# duck punch
_SignalTrackingMapperExtension._record = _record


class RockPackTestCase(unittest.TestCase):

    set_trace = pytest.set_trace

    def setUp(self):
        rockpack.mainsite.app.config['TESTING'] = True
        self.app = rockpack.mainsite.app
        self.session = db.session


class FixtureTestCase(RockPackTestCase, DataTestCase):
    def setUp(self):
        super(FixtureTestCase, self).setUp()
        data = self.fixture.data(*self.datasets)
        data.setup()
        self.data = data

    def tearDown(self):
        super(FixtureTestCase, self).tearDown()
        self.data.teardown()
