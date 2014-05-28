import time
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


@manager.cron_command(interval=900)
@job_control
def update_indexes(date_from=None, date_to=None):
    """ Updates all data in all indexes """
    start = time.time()
    helpers.full_user_import(start=date_from, stop=date_to)
    helpers.full_channel_import(start=date_from, stop=date_to)
    helpers.full_video_import(start=date_from, stop=date_to)
    app.logger.info('Ran update_indexes in %ds', time.time() - start)


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
