import os
import gzip
from datetime import datetime, timedelta
from pkg_resources import resource_filename
from subprocess import check_output
from tempfile import gettempdir
from rockpack.mainsite import app
from rockpack.mainsite.manager import manager
from rockpack.mainsite.core.dbapi import commit_on_success
from .models import AppDownloadRecord


ITUNES_PROD_TYPE_TO_ACTION = {'1F': 'download', '7F': 'update'}


def _download_report(username, password, vendor, date):
    # Use Autoingestion.class from Apple to download the data
    tmp = gettempdir()
    ingest_class = resource_filename(__name__, 'Autoingestion.class')
    classpath, filename = os.path.split(ingest_class)
    classname = os.path.splitext(filename)[0]
    output = check_output([
        'java', '-cp', os.path.abspath(classpath), classname, username, password,
        vendor, 'Sales', 'Daily', 'Summary', date.strftime('%Y%m%d')],
        cwd=tmp)
    output_lines = output.strip().split('\n')
    if 'Success' not in output_lines[-1]:
        raise Exception(output_lines[-1])
    return os.path.join(tmp, output_lines[-2])


@commit_on_success
def _import_records(filename):
    session = AppDownloadRecord.query.session
    with gzip.open(filename) as datafile:
        for line in datafile:
            if line.startswith('APPLE'):
                datarow = line.split('\t')
                session.add(AppDownloadRecord(
                    source='itunes',
                    version=datarow[5],
                    action=ITUNES_PROD_TYPE_TO_ACTION[datarow[6]],
                    country=datarow[12],
                    date=datetime.strptime(datarow[10], '%m/%d/%Y'),
                    count=int(datarow[7]),
                ))


@manager.cron_command(interval=86400)
def import_itunes_downloads(date=None):
    if 'ITUNES_CONNECT_PASSWORD' not in app.config:
        app.logger.info('No iTunes credentials configured')
        return
    username = app.config['ITUNES_CONNECT_APPLEID']
    password = app.config['ITUNES_CONNECT_PASSWORD']
    vendor = app.config['ITUNES_CONNECT_VENDORID']

    if date:
        date = datetime.strptime(date, '%Y-%m-%d')
    else:
        date = datetime.today() - timedelta(days=1)

    report = _download_report(username, password, vendor, date)
    _import_records(report)
    os.unlink(report)
