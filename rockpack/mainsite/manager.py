import os
import sys
import logging
from datetime import datetime
from functools import wraps
from sqlalchemy import func
from wonder.common.commands import Manager
from rockpack.mainsite import app, init_app, settings
from rockpack.mainsite.core.dbapi import commit_on_success
from rockpack.mainsite.helpers.db import resize_and_upload
from rockpack.mainsite.helpers.http import get_external_resource
from rockpack.mainsite.services.base.models import JobControl


manager = Manager(app, reloader_extra_files=settings)


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
    env = os.environ
    env['PATH'] = '/usr/bin:/bin'
    args = ['psql']
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
    if map_only:
        helpers.Indexing.create_all_mappings()
    else:
        helpers.Indexing.create_all_indexes(rebuild=rebuild)


@manager.option('-c', '--channels-only', action='store_true')
@manager.option('-v', '--videos-only', action='store_true')
@manager.option('-u', '--users-only', action='store_true')
@manager.option('-s', '--stars-only', action='store_true')
@manager.option('-r', '--restrictions-only', action='store_true')
@manager.option('-l', '--shares-only', action='store_true')
@manager.option('-t', '--terms-for-channel-only', action='store_true')
@manager.option('--suggestions-only', action='store_true')
@manager.command
def import_to_es(prefix=None, **kwargs):
    """Import data into elasticsearch from the db"""
    # NOTE: change this to be sensible
    from rockpack.mainsite.core.es import helpers
    i = helpers.DBImport()

    if kwargs['terms_for_channel_only']:
        i.import_video_channel_terms()
        return

    if kwargs['stars_only']:
        i.import_video_stars()
        return

    if kwargs['restrictions_only']:
        i.import_video_restrictions()
        return

    if kwargs['shares_only']:
        i.import_channel_share()
        return

    if kwargs['suggestions_only']:
        i.import_search_suggestions()
        return

    if not (kwargs['videos_only'] or kwargs['users_only']):
        helpers.full_channel_import()
    if not (kwargs['channels_only'] or kwargs['users_only']):
        helpers.full_video_import(prefix=prefix)
    if not (kwargs['channels_only'] or kwargs['videos_only']):
        helpers.full_user_import()


@manager.command
def print_model_shards(length=3, video=False, channel=False):
    if channel:
        from rockpack.mainsite.services.video.models import Channel as model
    else:
        from rockpack.mainsite.services.video.models import VideoInstance as model
    for shard, in model.query.distinct().values(func.substring(model.id, 1, length)):
        print shard


def _parse_fieldname(fieldname):
    from rockpack.mainsite.services.user import api
    try:
        model, fieldname = fieldname.split('.')
        model = getattr(api, model)
        getattr(model, fieldname)
    except Exception, e:
        print >>sys.stderr, 'Invalid field name: %s: %s' % (fieldname, e)
        sys.exit(2)
    cfgkey = model.__table__.columns.get(fieldname).type.cfgkey
    return model, fieldname, cfgkey


@manager.command
def update_image_thumbnails(fieldname):
    """Re-process all images for the specified Model.field."""
    model, fieldname, cfgkey = _parse_fieldname(fieldname)
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
def upload_default_image(fieldname, filename, name=None):
    model, fieldname, cfgkey = _parse_fieldname(fieldname)
    with open(filename) as img:
        resize_and_upload(img, cfgkey, name=name)


@manager.option('--channel')
@manager.option('--user')
@manager.option('--title')
@manager.option('--category')
@manager.option('--label')
@manager.command
def import_video(s3path, **options):
    from rockpack.mainsite.core.ooyala import create_asset
    create_asset(s3path, options)


@manager.command
def update_ooyala_thumbnails(videoid):
    from rockpack.mainsite.services.video.models import Video
    from rockpack.mainsite.core.es.api import es_update_channel_videos
    from rockpack.mainsite.core.ooyala import update_thumbnails
    if videoid == 'all':
        args = dict()
    elif len(videoid) == 32:    # ooyala embed_code
        args = dict(source_videoid=videoid)
    else:
        args = dict(id=videoid)
    for video in Video.query.filter_by(source=2, **args):
        update_thumbnails(video)
        video.save()
        es_update_channel_videos([v.id for v in video.instances])


def run(*args):
    init_app()
    if args:
        return manager.handle(sys.argv[0], args)
    else:
        return manager.run()
