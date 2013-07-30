import sys
import logging
from flask.ext.script import Manager as BaseManager
from flask.ext.assets import ManageAssets
from rockpack.mainsite import app, init_app
from rockpack.mainsite.helpers.db import resize_and_upload
from rockpack.mainsite.helpers.http import get_external_resource


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


@manager.command
def init_es(rebuild=False, map_only=False):
    """Initialise elasticsearch indexes"""
    from rockpack.mainsite.core.es import helpers
    i = helpers.Indexing()
    if not map_only:
        i.create_all_indexes(rebuild=rebuild)
    i.create_all_mappings()


@manager.command
def import_to_es(channels_only=False, videos_only=False, owners_only=False, stars_only=False):
    """Import data into elasticsearch from the db"""
    from rockpack.mainsite.core.es import helpers
    i = helpers.DBImport()
    if not stars_only:
        if not (videos_only or owners_only):
            i.import_channels()
        if not (channels_only or owners_only):
            i.import_videos()
        if not (channels_only or videos_only):
            i.import_owners()

    if stars_only:
        i.import_video_stars()


@manager.command
def update_image_thumbnails(fieldname):
    """Re-process all images for the specified Model.field."""
    from rockpack.mainsite.services.user import api
    try:
        model, fieldname = fieldname.split('.')
        model = getattr(api, model)
        getattr(model, fieldname)
    except Exception, e:
        print >>sys.stderr, 'Invalid field name: %s: %s' % (fieldname, e)
        sys.exit(2)

    cfgkey = model.__table__.columns.get(fieldname).type.cfgkey
    for instance in model.query.filter(getattr(model, fieldname) != ''):
        try:
            data = get_external_resource(getattr(instance, fieldname).original)
        except Exception, e:
            msg = e.response.reason if hasattr(e, 'response') else e.message
            logging.error('Unable to process %s: %s', getattr(instance, fieldname).path, msg)
            continue
        aoi = getattr(instance, '%s_aoi' % fieldname, None)
        image_path = resize_and_upload(data, cfgkey, aoi)
        setattr(instance, fieldname, image_path)
        instance.save()


def run(*args):
    init_app()
    if args:
        return manager.handle(sys.argv[0], args[0], args[1:])
    else:
        return manager.run()
