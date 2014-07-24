import time
from datetime import timedelta
from functools import wraps
from rockpack.mainsite import app
from rockpack.mainsite.manager import manager, job_control
from rockpack.mainsite.core.es import helpers


def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        func(*args, **kwargs)
        app.logger.info('Ran %s in %fs', func.func_name, time.time() - start)
    return wrapper


@manager.cron_command(interval=60)
@job_control
def update_indexes(date_from=None, date_to=None):
    """Updates all data in all indexes"""
    start_time = time.time()
    # Split up into 60 second intervals
    start = date_to
    while start > date_from:
        stop = start
        start -= timedelta(seconds=100)
        if start < date_from:
            start = date_from
        app.logger.info('Index update interval: %s -> %s (%ds)',
                        start.time(), stop.time(), (stop - start).seconds)
        helpers.full_user_import(start=start, stop=stop)
        helpers.full_channel_import(start=start, stop=stop)
        helpers.full_video_import(start=start, stop=stop)
    app.logger.info('Ran update_indexes in %ds', time.time() - start_time)


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
