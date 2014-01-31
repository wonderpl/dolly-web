from datetime import datetime, timedelta
from urlparse import urljoin
import urllib
from flask import request, abort
from rockpack.mainsite.core import ooyala
from rockpack.mainsite.helpers.urls import url_for
from rockpack.mainsite.core.webservice import WebService, expose_ajax, secure_view
from rockpack.mainsite.services.video import models
from rockpack.mainsite.services.user.models import User


class MissingDateRange(Exception):
    pass


DATE_FORMAT = '%Y-%m-%d'


def _format_dates(start, end):
    sanitised_dates = []
    for d in [start, end]:
        if isinstance(d, datetime):
            sanitised_dates.append(d.strftime(DATE_FORMAT))
        else:
            sanitised_dates.append(d)

    date_range = '...'.join(filter(None, sanitised_dates))
    if not date_range:
        raise MissingDateRange

    return date_range


def _videos_request(feed, path='', breakdown_by=''):
    return ooyala._ooyala_feed(feed, path, query_params=dict(breakdown_by=breakdown_by))


def _video_data_transform(d):
    metrics = d['metrics']['video']
    return {
        'plays': metrics.get('plays', 0),
        'daily_uniq_plays': metrics.get('uniq_plays', {}).get('daily_uniqs', 0),
        'weekly_uniq_plays': metrics.get('uniq_plays', {}).get('weekly_uniqs', 0),
        'monthly_uniq_plays': metrics.get('uniq_plays', {}).get('monthly_uniqs', 0),
        'playthrough_100': metrics.get('playthrough_100', 0),
        'playthrough_75': metrics.get('playthrough_75', 0),
        'playthrough_50': metrics.get('playthrough_50', 0),
        'playthrough_25': metrics.get('playthrough_25', 0),
    }


def _process_individual(data):
    metrics = data['results']['total']
    result = []
    for m in metrics:
        r = dict(date=m['date'])
        if m.get('metrics'):
            r.update(_video_data_transform(m))
        result.append(r)
    return dict(metrics=result)


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
        if d.get('name'):
            transformed_data[video_id] = d['name']
    return transformed_data


def videos_total(start, end=None):
    path = 'reports/account/performance/videos/%s' % (_format_dates(start, end))
    return _process_total(_videos_request('analytics', path))


def videos_individual(resource_id, start, end=None):
    path = 'reports/asset/%s/performance/total/%s' % (resource_id, _format_dates(start, end))
    return _process_individual(_videos_request('analytics', path, breakdown_by='day'))


class Analytics(WebService):

    endpoint = '/analytics'

    @expose_ajax('/<user_id>/')
    def video_all(self, user_id):
        labels = _videos_request('labels')
        label_id = None
        for label in labels['items']:
            if label['name'] == 'Lucas Hugh':
                label_id = label['id']
                break
        if not label_id:
            abort(404)

        BASE_URL = url_for('basews.discover')

        raw_video_data = _videos_request('labels', label_id + '/assets')
        response_data = []
        for video in raw_video_data.get('items'):
            resource_url = urljoin(
                BASE_URL,
                url_for('analytics.video_individual', user_id='-', video_id=video['embed_code'])
            )
            response_data.append(
                dict(
                    date_uploaded=video['created_at'],
                    duration=video['duration'],
                    embed_code=video['embed_code'],
                    name=video['name'],
                    thumbnail_url=video['preview_image_url'],
                    resource_url=resource_url,
                    resource_url_weekly=resource_url + '?' + urllib.urlencode(
                        {'start': (datetime.now() - timedelta(days=7)).strftime(DATE_FORMAT),
                            'end': datetime.now().strftime(DATE_FORMAT)})
                )
            )
        return dict(videos=dict(items=response_data))

    @expose_ajax('/<user_id>/<video_id>/')
    def video_individual(self, user_id, video_id):
        try:
            video_id = [_ for _ in models.Video.query.join(
                models.Source, models.Source.id == models.Video.source
            ).join(
                models.VideoInstance, models.VideoInstance.video == models.Video.id
            ).join(
                models.Channel,
                (models.Channel.id == models.VideoInstance.channel) &
                (models.Channel.owner == user_id)
            ).filter(
                models.VideoInstance.id == video_id,
                models.Source.label == 'ooyala',
            ).values(models.Video.source_videoid)][0]
        except IndexError:
            pass

        data = videos_individual(video_id, request.args.get('start', datetime.now()), request.args.get('end', None))
        return data
