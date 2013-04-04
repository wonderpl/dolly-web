import sys
import logging
from flask.ext.script import Manager
from flask.ext.assets import ManageAssets
from rockpack.mainsite import app, init_app

manager = Manager(app)
manager.add_command("assets", ManageAssets())
manager.logger = app.logger.manager.getLogger('command')


@manager.command
def test():
    """Run tests"""
    import pytest
    pytest.main()


@manager.command
def recreate_db(options):
    """Drops and re-creates database"""
    from rockpack import mainsite
    from rockpack.mainsite.core import dbapi
    db_url = mainsite.app.config['DATABASE_URL']
    answer = ''
    while answer not in ['y', 'n']:
        answer = raw_input("Are you sure you want to do this"
                           " (this will nuke '{}')? [Y/N]".format(db_url.rsplit('/', 1)[1]))
    dbapi.create_database(db_url, drop_if_exists=answer.lower() == 'y')


@manager.command
def syncdb(options):
    """Create all db tables"""
    from rockpack.mainsite.core import dbapi
    dbapi.sync_database()


def run(*args):
    init_app()
    logging.basicConfig(level=logging.INFO if app.debug else logging.WARN)
    if args:
        return manager.handle(sys.argv[0], args[0], args[1:])
    else:
        return manager.run()
