import sys
import psycopg2
from functools import wraps

from sqlalchemy import create_engine, schema
from sqlalchemy.orm import sessionmaker, scoped_session, class_mapper, defer
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


def sync_database(drop_all=False, custom_modules=None):
    models = []

    def load_modules(module):
        try:
            models.append(__import__(module + '.models', fromlist=['models']))
        except ImportError as e:
            #print >> sys.stderr, 'cannot import', module, ':', e
            pass

    modules = custom_modules or SERVICES + zip(*REGISTER_SETUPS)[0]
    for module in modules:
        # HACK: prevent admin modules being loaded unless explicitly passed
        # Stops CMS class instantiation breaking tests.
        if not custom_modules and module in ('rockpack.mainsite.admin', 'rockpack.mainsite.admin.auth', ):
            continue
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

    def add(self):
        self.query.session.add(self)
        return self


sqlalchemy.Model = _Model

db = get_sessionmanager()


def get_slave_session():
    url = app.config.get('SLAVE_DATABASE_URL', None)
    if url:
        return scoped_session(sessionmaker(bind=create_engine(url), autoflush=False))


readonly_session = get_slave_session() or db.session


@app.teardown_appcontext
def remove_readonly(response):
    readonly_session.remove()
    return response


@app.before_request
def add_session_to_request_g():
    g.session = db.session


def commit_on_success(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
            db.session.commit()
        except:
            etype, evalue, traceback = sys.exc_info()
            try:
                db.session.rollback()
            except:
                pass
            raise etype(*evalue.args), None, traceback
        else:
            return result
    return wrapper


def defer_except(entity, cols):
    # see http://www.sqlalchemy.org/trac/ticket/1418
    m = class_mapper(entity)
    return [defer(k) for k in
            set(p.key for p in m.iterate_properties
                if hasattr(p, 'columns')).difference(cols)]
