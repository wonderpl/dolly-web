import time
from functools import wraps
from rockpack.mainsite import app
from rockpack.mainsite.manager import manager
from rockpack.mainsite.core.es import helpers

def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        func(*args, **kwargs)
        app.logger.info('Ran import_video_repins in %fs', time.time() - start)
    return wrapper

@manager.command
@timer
def import_video_repins():
    helpers.DBImport().import_dolly_repin_counts()

@manager.command
@timer
def import_video_repin_owners():
    helpers.DBImport().import_dolly_video_owners()
