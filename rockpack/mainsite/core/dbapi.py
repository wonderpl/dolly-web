import sys
import psycopg2
from functools import wraps

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base

from flask.ext.sqlalchemy import SQLAlchemy
from flask import g

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
        return g.session.query(cls).get(id)

    def save(self):
        g.session.merge(self)      # XXX: Use session.add?
        return g.session.commit()  # XXX: commit here or leave to view to handle?


Base = declarative_base(cls=_Base)


def get_sessionmanager(config=app.config['DATABASE_URL']):
    app.config['SQLALCHEMY_DATABASE_URI'] = config
    return SQLAlchemy(app)


db = get_sessionmanager()


@app.before_request
def add_session_to_request_g():
    g.session = db.session


def commit_on_success(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
        except Exception:
            g.session.rollback()
            raise
        else:
            g.session.commit()
            return result
    return wrapper
