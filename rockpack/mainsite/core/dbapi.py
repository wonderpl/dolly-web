import sys
import psycopg2
from functools import wraps

from sqlalchemy import create_engine

from flask.ext import sqlalchemy
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


def get_sessionmanager(config=app.config['DATABASE_URL']):
    app.config['SQLALCHEMY_DATABASE_URI'] = config
    return sqlalchemy.SQLAlchemy(app)


class _Model(sqlalchemy.Model):
    @classmethod
    def get(cls, id):
        return g.session.query(cls).get(id)

    def save(self):
        g.session.add(self)
        return g.session.commit()


sqlalchemy.Model = _Model
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
