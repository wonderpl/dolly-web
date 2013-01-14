#!/usr/bin/env python
import sys
import argparse

import sqlalchemy

from rockpack.core.dbapi import Base
from rockpack.core.dbapi import db_engine

def dbsync(module_with_models):
    if not module_with_models:
        return

    try:
        models =  __import__(module_with_models + '.models', fromlist=['models'])
    except ImportError as e:
        print >> sys.stderr, 'cannot import', module_with_models
        sys.exit(1)

    table_list = []
    for item in models.__dict__.itervalues():
        try:
            if (isinstance(item, type) and issubclass(item, Base)
                    and hasattr(item, '__table__') and isinstance(item.__table__, sqlalchemy.schema.Table)):
                table = item.__table__
                table_list.append(table)
        except TypeError:
            continue

    try:
        if table_list:
            Base.metadata.create_all(db_engine, tables=table_list, checkfirst=True)
        else:
            print >> sys.stderr, 'no tables to build'
    except Exception as e:
        print >> sys.stderr, 'failed to build tables with:', str(e)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dbsync', help='modules containing models')
    args = parser.parse_args()
    dbsync(args.dbsync)


if __name__ == '__main__':
    main()
