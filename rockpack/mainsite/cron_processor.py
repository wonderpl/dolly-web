import logging
from wonder.common.cron import CronProcessor
from rockpack.mainsite import app, init_app
from rockpack.mainsite.manager import manager
from rockpack.mainsite.services.base.models import JobControl
from rockpack.mainsite.core.es import discover_cluster_nodes


def create_app():
    # uwsgi mule will execute here
    if not app.blueprints:
        init_app()

    if 'SENTRY_DSN' in app.config:
        from raven.contrib.flask import Sentry
        Sentry(app, logging=app.config.get('SENTRY_ENABLE_LOGGING'), level=logging.WARN)

    # Use ES cluster nodes directly for batch jobs
    discover_cluster_nodes()

    return app


if __name__ == '__main__':
    CronProcessor(manager, JobControl, create_app).run()
