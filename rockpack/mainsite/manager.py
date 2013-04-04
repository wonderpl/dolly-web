import sys
import logging
from flask.ext.script import Manager as BaseManager
from flask.ext.assets import ManageAssets
from rockpack.mainsite import app, init_app


class Manager(BaseManager):
    def __init__(self, app):
        super(Manager, self).__init__(app)
        self.add_command("assets", ManageAssets())
        self.logger = app.logger.manager.getLogger('command')
        self._cron_commands = []

    def cron_command(self, f):
        self._cron_commands.append(f.__name__)
        return self.command(f)

    def handle(self, prog, name, args=None):
        logging.basicConfig(level=logging.INFO if app.debug else logging.WARN)
        if name in self._cron_commands and not self.app.config.get('ENABLE_CRON_JOBS'):
            logging.info('cron jobs not enabled')
            return
        return super(Manager, self).handle(prog, name, args)

manager = Manager(app)


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
    if args:
        return manager.handle(sys.argv[0], args[0], args[1:])
    else:
        return manager.run()
