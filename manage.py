#!/usr/bin/env python
import argparse


def test(options):
    import pytest
    pytest.main(options[1])


def recreate_db(options):
    from rockpack import mainsite
    from rockpack.mainsite.core import dbapi
    db_url = mainsite.app.config['DATABASE_URL']
    answer = ''
    while answer not in ['y', 'n']:
        answer = raw_input("Are you sure you want to do this"
                           " (this will nuke '{}')? [Y/N]".format(db_url.rsplit('/', 1)[1]))
    dbapi.create_database(db_url, drop_if_exists=answer.lower() == 'y')


def dbsync(options):
    from rockpack.mainsite.core import dbapi
    dbapi.sync_database()


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
