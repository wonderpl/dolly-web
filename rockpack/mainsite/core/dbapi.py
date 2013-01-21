import sys
import psycopg2
from functools import wraps
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.ext.declarative import declarative_base

from rockpack.mainsite import app


def drop_database(db_url):
    base, db_name = db_url.rsplit('/', 1)
    engine = create_engine(base + '/template1')
    command = 'DROP DATABASE IF EXISTS {}'.format(db_name)
    engine.raw_connection().set_isolation_level(
        psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    print >> sys.stdout, command
    engine.execute(command)
    engine.dispose()


def create_database(db_url, drop_if_exists=False):
    base, db_name = db_url.rsplit('/', 1)
    if drop_if_exists:
        drop_database(db_url)
    engine = create_engine(base + '/template1')     # hack for now
    command = 'CREATE DATABASE {}'.format(db_name)
    engine.raw_connection().set_isolation_level(
        psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    print >> sys.stdout, command
    engine.execute(command)


class _Base(object):

    @classmethod
    def get(cls, id):
        return session.query(cls).get(id)

    def save(self):
        session.merge(self)      # XXX: Use session.add?
        return session.commit()  # XXX: commit here or leave to view to handle?


Base = declarative_base(cls=_Base)


class SessionManager(object):
    def __init__(self, connection_string):
        self.connection_string = connection_string
        self._Session = scoped_session(sessionmaker())

    def get_engine(self):
        try:
            engine = self.engine
        except AttributeError:
            engine = self.engine = create_engine(self.connection_string)
        return engine

    def get_session(self):
        self._Session.configure(bind=self.get_engine())
        return self._Session()


manager = SessionManager(app.config['DATABASE_URL'])

# Only return the func so that we don't
# commit to this engine now, in case we
# want to change it after after
# SessionManager is instantiated
get_engine = manager.get_engine
session = manager.get_session()


def commit_on_success(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
        except Exception:
            session.rollback()
            raise
        else:
            session.commit()
            return result
    return wrapper
