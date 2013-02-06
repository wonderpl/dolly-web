#!/usr/bin/env python
import sys
import argparse

import sqlalchemy


required_modules = ['rockpack.mainsite.auth', 'rockpack.mainsite.admin']


def dbsync(options):
    from rockpack.mainsite.core.dbapi import db
    from rockpack.mainsite import SERVICES, REGISTER_SETUPS

    models = []

    def load_modules(module):
        try:
            models.append(__import__(module + '.models', fromlist=['models']))
        except ImportError as e:
            print >> sys.stderr, 'cannot import', module, ':', e

    for module in SERVICES + zip(*REGISTER_SETUPS)[0]:
        load_modules(module)

    table_list = []
    for model in models:
        for item in model.__dict__.itervalues():
            try:
                if (isinstance(item, type) and issubclass(item, db.Model)
                        and hasattr(item, '__table__')
                        and isinstance(item.__table__, sqlalchemy.schema.Table)):
                    table = item.__table__
                    table_list.append(table)
            except TypeError:
                continue

    try:
        if table_list:
            db.Model.metadata.create_all(db.engine, tables=table_list, checkfirst=True)
        else:
            print >> sys.stderr, 'no tables to build'
    except Exception as e:
        print >> sys.stderr, 'failed to build tables with:', str(e)


def create_database(db_url, drop_first=False):
    from rockpack.mainsite.core import dbapi
    if drop_first:
        dbapi.create_database(db_url, drop_if_exists=True)
    else:
        dbapi.create_database(db_url)


def _patch_db_url(db_url):
    from rockpack.mainsite.core import dbapi
    dbapi.db = dbapi.get_sessionmanager(db_url)


def test(options):
    import pytest
    from rockpack import mainsite
    mainsite.app.config['TESTING'] = True
    db_url = mainsite.app.config['TEST_DATABASE_URL']
    _patch_db_url(db_url)
    create_database(db_url, drop_first=True)
    dbsync(None)
    mainsite.init_app()
    from test.fixtures import install, all_data
    install(*all_data)
    pytest.main(options[1])


def recreate_db(options):
    from rockpack import mainsite
    db_url = mainsite.app.config['DATABASE_URL']
    answer = ''
    while answer not in ['y', 'n']:
        answer = raw_input("Are you sure you want to do this"
                           " (this will nuke '{}')? [Y/N]".format(db_url.rsplit('/', 1)[1]))

    if answer.lower() == 'y':
        create_database(db_url, drop_first=True)
    else:
        create_database(db_url)


def main():
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers()
    test_parser = subparsers.add_parser('test', help='run pytests')
    test_parser.set_defaults(func=test)

    sync_parser = subparsers.add_parser('dbsync', help='syncs tables')
    sync_parser.set_defaults(func=dbsync)

    recreatedb_parser = subparsers.add_parser('recreatedb', help='drops and re-creates database')
    recreatedb_parser.set_defaults(func=recreate_db)

    args = parser.parse_known_args()
    args[0].func(args)
    parser.exit(1)


if __name__ == '__main__':
    main()
