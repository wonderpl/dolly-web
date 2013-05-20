import sys
import psycopg2
from functools import wraps

from sqlalchemy import create_engine, schema
from sqlalchemy.exc import StatementError
from werkzeug.exceptions import HTTPException
from flask.ext import sqlalchemy
from flask import g

from rockpack.mainsite import app, SERVICES, REGISTER_SETUPS


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


def sync_database(drop_all=False):
    models = []

    def load_modules(module):
        try:
            models.append(__import__(module + '.models', fromlist=['models']))
        except ImportError as e:
            #print >> sys.stderr, 'cannot import', module, ':', e
            pass

    for module in SERVICES + zip(*REGISTER_SETUPS)[0]:
        load_modules(module)

    table_list = []
    for model in models:
        for item in model.__dict__.itervalues():
            try:
                if (isinstance(item, type) and issubclass(item, db.Model)
                        and hasattr(item, '__table__')
                        and isinstance(item.__table__, schema.Table)):
                    table = item.__table__
                    table_list.append(table)
            except TypeError:
                continue

    try:
        if table_list:
            if drop_all:
                db.Model.metadata.drop_all(db.engine)
            db.Model.metadata.create_all(db.engine, tables=table_list, checkfirst=True)
        else:
            print >> sys.stderr, 'no tables to build'
    except Exception as e:
        print >> sys.stderr, 'failed to build tables with:', str(e)


def get_sessionmanager(config=app.config['DATABASE_URL']):
    app.config['SQLALCHEMY_DATABASE_URI'] = config
    db = sqlalchemy.SQLAlchemy(app)
    if app.config.get('USE_GEVENT'):
        db.engine.pool._use_threadlocal = True
    return db


class _Model(sqlalchemy.Model):

    def save(self):
        session = self.query.session
        merged = session.merge(self)
        try:
            # commit is called here so that we can get the id of the new record
            session.commit()
        except StatementError, e:
            # Check if the statement value bind mapping threw a bad request
            if isinstance(e.orig, HTTPException):
                raise e.orig
            else:
                raise
        return merged


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
            db.session.rollback()
            raise
        else:
            db.session.commit()
            return result
    return wrapper
