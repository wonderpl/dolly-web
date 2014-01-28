from datetime import datetime
from flask import request
from rockpack.mainsite.core import ooyala
from rockpack.mainsite.core.webservice import WebService, expose_ajax, secure_view


class MissingDateRange(Exception):
    pass


def _format_dates(start, end):
    sanitised_dates = []
    for d in [start, end]:
        if isinstance(d, datetime):
            sanitised_dates.append(d.strftime('%y-%m-%d'))
        else:
            sanitised_dates.append(d)

    date_range = '...'.join(filter(None, sanitised_dates))
    if not date_range:
        raise MissingDateRange

    return date_range


def _videos_request(path):
    print '------------path', path
    return ooyala._ooyala_feed('analytics', path)


def _video_data_transform(d):
    metrics = d['metrics']['video']
    return {
        'plays': metrics['plays'],
        'daily_uniq_plays': metrics['uniq_plays']['daily_uniqs'],
        'weekly_uniq_plays': metrics['uniq_plays']['weekly_uniqs'],
        'monthly_uniq_plays': metrics['uniq_plays']['monthly_uniqs'],
        'playthrough_100': metrics.get('playthrough_100', 0),
        'playthrough_75': metrics.get('playthrough_75', 0),
        'playthrough_50': metrics.get('playthrough_50', 0),
        'playthrough_25': metrics.get('playthrough_25', 0),
    }


def _process_individual(data):
    metrics = data['results'][0]
    return dict(metrics=_video_data_transform(metrics))


def _process_total(data):
    transformed_data = {}
    for d in data.get('results'):
        try:
            video_id = d['movie_data']['embed_code']
        except:  # missing data, skip
            continue
        transformed_data.update({
            video_id: {
                'name': d['name'],
                'metrics': _video_data_transform(d)
            }
        })
    return transformed_data


def videos_total(start, end=None):
    path = 'reports/account/performance/videos/%s' % (_format_dates(start, end))
    return _process_total(_videos_request(path))


def videos_individual(resource_id, start, end=None):
    path = 'reports/asset/%s/performance/total/%s' % (resource_id, _format_dates(start, end)
    )
    return _process_individual(_videos_request(path))


class Analytics(WebService):

    endpoint = '/analytics'

    @expose_ajax('/')
    def video_all(self):
        data = videos_total(request.args.get('start'), request.args.get('end', None))
        return dict(videos=dict(items=data))

    @expose_ajax('/<video_id>/')
    def video_individual(self, video_id):
        data = videos_individual(video_id, request.args.get('start'), request.args.get('end', None))
        return data
