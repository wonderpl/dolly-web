import sys
import time
import signal
import logging
from datetime import datetime, timedelta
from sqlalchemy import func
from rockpack.mainsite import app, init_app
from rockpack.mainsite.core.dbapi import db
from rockpack.mainsite.core.timing import record_timing
from rockpack.mainsite.manager import manager
from rockpack.mainsite.services.base.models import JobControl


def _pg_lock(lock, f):
    query = 'select %s(%d);' % (f, hash(lock))
    return db.session.execute(query).fetchone()[0]
lock_command = lambda command: _pg_lock(command, 'pg_try_advisory_lock')
unlock_command = lambda command: _pg_lock(command, 'pg_advisory_unlock')


def _hup_handler(sighup, frame):
    global _hup_received
    _hup_received = True
_hup_received = False


def process_next_job():
    cron_commands = manager.get_cron_commands()
    enabled_jobs = set(cron_commands.keys()) - set(app.config.get('DISABLED_CRON_JOBS', []))
    job = JobControl.query.filter(
        JobControl.next_run <= func.now(),
        JobControl.job.in_(enabled_jobs),
    ).order_by(func.random()).first()   # random used to avoid getting stuck on long running jobs
    if not job:
        return

    command = job.job
    interval = cron_commands[command]

    acquired = lock_command(command)
    if not acquired:
        # somebody else is processing this job
        return

    start_time = time.time()
    try:
        manager.handle('cron', [command])
    except Exception:
        app.logger.exception('Failed to run command: %s', command)
        success = False
    else:
        job.next_run = datetime.now() + timedelta(seconds=interval)
        db.session.commit()
        success = True
    finally:
        assert unlock_command(command)

    record_timing('cron_processor.%s.run_time' % command, time.time() - start_time)

    return success


def run():
    # uwsgi mule will execute here
    if not app.blueprints:
        init_app()

    # Catch HUP from uwsgi
    signal.signal(signal.SIGHUP, _hup_handler)

    if 'SENTRY_DSN' in app.config:
        from raven.contrib.flask import Sentry
        Sentry(app, logging=app.config.get('SENTRY_ENABLE_LOGGING'), level=logging.WARN)

    while True:
        with app.app_context():
            success = process_next_job()
        if not success and not _hup_received:
            time.sleep(10)
        if _hup_received:
            sys.exit()


if __name__ == '__main__':
    run()
