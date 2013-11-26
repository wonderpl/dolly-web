import os
import sys
import logging
from datetime import datetime
from functools import wraps
from sqlalchemy import func
from flask.ext.script import Manager as BaseManager
from flask.ext.assets import ManageAssets
from rockpack.mainsite import app, init_app
from rockpack.mainsite.core.dbapi import commit_on_success
from rockpack.mainsite.helpers.db import resize_and_upload
from rockpack.mainsite.helpers.http import get_external_resource
from rockpack.mainsite.services.base.models import JobControl


class Manager(BaseManager):
    def __init__(self, app):
        super(Manager, self).__init__(app)
        self.add_command("assets", ManageAssets())
        self.logger = app.logger.manager.getLogger('command')
        self._cron_commands = {}

    def cron_command(self, interval=None):
        def decorator(f):
            self._cron_commands[f.__name__] = interval
            return self.command(f)
        return decorator

    def get_cron_commands(self):
        return self._cron_commands

    def handle(self, prog, name, args=None):
        logging.basicConfig(level=logging.INFO if app.debug else logging.WARN)
        return super(Manager, self).handle(prog, name, args)

manager = Manager(app)


def job_control(f):
    """Wrap the given function to ensure the input data is limited to a specific interval."""
    @wraps(f)
    @commit_on_success
    def wrapper():
        now = datetime.utcnow()
        job_name = f.__name__
        job_control = JobControl.query.get(job_name)
        if not job_control:
            job_control = JobControl(job=job_name, last_run=now).add()
        app.logger.info('%s: from %s to %s', job_name, job_control.last_run, now)

        f(job_control.last_run, now)

        # XXX: If the cron function throws an exception then last_run is not saved
        # and the job will be retried next time, including the same interval.
        job_control.last_run = now
    return wrapper


@manager.command
def test():
    """Run tests"""
    import pytest
    pytest.main()


@manager.command
def recreate_db():
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
def syncdb():
    """Create all db tables"""
    from rockpack.mainsite.core import dbapi
    dbapi.sync_database()


@manager.command
def dbshell(slave=False):
    """Run psql for the mainsite database."""
    from sqlalchemy import create_engine
    dburl = app.config['SLAVE_DATABASE_URL' if slave else 'DATABASE_URL']
    engine = create_engine(dburl)
    assert engine.dialect.name == 'postgresql'
    args, env = ['psql'], {'PATH': '/usr/bin:/bin'}
    if engine.url.username:
        args += ['-U', engine.url.username]
    if engine.url.host:
        args.extend(['-h', engine.url.host])
    if engine.url.port:
        args.extend(['-p', str(engine.url.port)])
    if engine.url.password:
        env['PGPASSWORD'] = engine.url.password
    args += [engine.url.database]
    try:
        os.execvpe(args[0], args, env)
    except OSError, e:
        print >>sys.stderr, '%s: %s' % (args[0], e.args[1])


@manager.command
def init_es(rebuild=False, map_only=False):
    """Initialise elasticsearch indexes"""
    from rockpack.mainsite.core.es import helpers
    i = helpers.Indexing()
    if not map_only:
        i.create_all_indexes(rebuild=rebuild)
    i.create_all_mappings()


@manager.command
def import_to_es(channels_only=False, videos_only=False, users_only=False, stars_only=False, restrictions_only=False, lshares_only=False, terms_for_channel_only=False, prefix=None):
    """Import data into elasticsearch from the db"""
    # NOTE: change this to be sensible
    from rockpack.mainsite.core.es import helpers
    i = helpers.DBImport()

    if terms_for_channel_only:
        i.import_video_channel_terms()
        return

    if stars_only:
        i.import_video_stars()
        return

    if restrictions_only:
        i.import_video_restrictions()
        return

    if lshares_only:
        i.import_channel_share()
        return

    if not (videos_only or users_only):
        i.import_channels()
    if not (channels_only or users_only):
        i.import_videos(prefix)
    if not (channels_only or videos_only):
        i.import_users()


@manager.command
def print_model_shards(length=3, video=False, channel=False):
    if channel:
        from rockpack.mainsite.services.video.models import Channel as model
    else:
        from rockpack.mainsite.services.video.models import VideoInstance as model
    for shard, in model.query.distinct().values(func.substring(model.id, 1, length)):
        print shard


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


@manager.command
def seed_cron_queue(commands=None):
    """Seed the cron SQS queue with a message for the specified jobs."""
    from rockpack.mainsite.cron_sqs_processor import init_messages
    init_messages(commands and commands.split(','))


@manager.command
def clean_cron_queue():
    from rockpack.mainsite.cron_sqs_processor import clean_messages
    clean_messages()


def run(*args):
    init_app()
    if args:
        return manager.handle(sys.argv[0], args[0], args[1:])
    else:
        return manager.run()
