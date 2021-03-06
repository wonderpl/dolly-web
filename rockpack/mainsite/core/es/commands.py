import time
from datetime import datetime, timedelta
from functools import wraps
from wonder.common.timing import record_timing
from rockpack.mainsite import app
from rockpack.mainsite.manager import manager
from rockpack.mainsite.services.base.models import JobControl
from rockpack.mainsite.core.dbapi import commit_on_success
from rockpack.mainsite.core.es import helpers


def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        func(*args, **kwargs)
        app.logger.info('Ran %s in %fs', func.func_name, time.time() - start)
    return wrapper


@manager.cron_command(interval=5)
@commit_on_success
def update_indexes():
    """Updates all data in all indexes"""
    job_control = JobControl.query.get('update_indexes')
    start = job_control.last_run
    stop = start + timedelta(seconds=60)
    delay = datetime.utcnow() - stop
    if delay < timedelta(0):
        return

    app.logger.info('update_indexes: from %s to %s', start, stop)

    start_time = time.time()
    helpers.full_user_import(start=start, stop=stop)
    helpers.full_channel_import(start=start, stop=stop)
    helpers.full_video_import(start=start, stop=stop)

    app.logger.info('update_indexes: ran in %ds: delay %ds',
                    time.time() - start_time, delay.total_seconds())
    record_timing('cron_processor.update_indexes.delay', delay.total_seconds())

    job_control.last_run = stop


@manager.command
@timer
def import_video_repins():
    helpers.DBImport().import_dolly_repin_counts()


@manager.command
def import_video_repin_owners(prefix=None):
    helpers.DBImport().import_dolly_video_owners(prefix)


@manager.command
@timer
def import_user_categories():
    helpers.DBImport().import_user_categories()


@manager.command
@timer
def import_average_category():
    helpers.DBImport().import_average_category()


@manager.command
def migrate_index(doc_type):
    helpers.ESMigration.migrate_alias(doc_type)


@manager.command
def import_comment_counts():
    helpers.DBImport().import_comment_counts()
