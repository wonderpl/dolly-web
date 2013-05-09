import re
from flask import request, json, Response
from rockpack.mainsite import app
from rockpack.mainsite.core.webservice import WebService, expose_ajax
from rockpack.mainsite.core import youtube
from rockpack.mainsite.helpers.db import gen_videoid
from rockpack.mainsite.services.video.api import get_local_channel
from rockpack.mainsite.services.video.models import Channel
from rockpack.mainsite.core.es.api import ChannelSearch
from rockpack.mainsite.core.es import filters


SEARCH_TERM_RE = re.compile('^[\w ]+$')

VIDEO_INSTANCE_PREFIX = 'Svi0xYzZY'


def _query_term(default=''):
    query = request.args.get('q', '')
    return query if SEARCH_TERM_RE.match(query) else default


class SearchWS(WebService):

    endpoint = '/search'

    default_page_size = 10
    max_page_size = 50

    @expose_ajax('/videos/', cache_age=300)
    def search_videos(self):
        """Search youtube videos."""
        order = 'published' if request.args.get('order') == 'latest' else None
        start, size = self.get_page()
        region = self.get_locale().split('-')[1]
        result = youtube.search(_query_term(), order, start, size,
                                region, request.remote_addr)
        items = []
        for position, video in enumerate(result.videos, start):
            items.append(
                dict(
                    position=position,
                    id='%s-%02d-%s' % (VIDEO_INSTANCE_PREFIX, 1, video.source_videoid),
                    title=video.title,
                    video=dict(
                        id=gen_videoid(None, 1, video.source_videoid),
                        source='youtube',
                        source_id=video.source_videoid,
                        source_date_uploaded=video.source_date_uploaded,
                        source_view_count=video.source_view_count,
                        source_username=video.source_username,
                        duration=video.duration,
                        thumbnail_url=video.default_thumbnail,
                    )
                )
            )
        return {'videos': {'items': items, 'total': result.video_count}}

    @expose_ajax('/channels/', cache_age=300)
    def search_channels(self):
        if app.config.get('ELASTICSEARCH_URL'):
            ch = ChannelSearch(self.get_locale())
            offset, limit = self.get_page()
            ch.set_paging(offset, limit)
            ch.add_text('title', _query_term().lower())
            ch.add_filter(filters.verified_channel_boost())
            if request.args.get('order') == 'latest':
                ch.date_sort('desc')
            channels = ch.channels(with_owners=True)
            return dict(channels=dict(items=channels, total=ch.total))

        # XXX: Obviously this needs to be replaced by a search engine
        date_order = True if request.args.get('order') == 'latest' else False
        items, total = get_local_channel(self.get_locale(),
                                         self.get_page(),
                                         query=_query_term(),
                                         date_order=date_order)
        return {'channels': {'items': items, 'total': total}}


class CompleteWS(WebService):

    endpoint = '/complete'

    @expose_ajax('/videos/', cache_age=3600)
    def complete_video_terms(self):
        # Client should hit youtube service directly because this service
        # is likely to be throttled by IP address
        result = youtube.complete(_query_term())
        return Response(result, mimetype='text/javascript')

    @expose_ajax('/channels/', cache_age=3600)
    def complete_channel_terms(self):
        # Use same javascript format as google complete for the sake of
        # consistency with /complete/videos
        query = _query_term()
        channels = Channel.query.filter(Channel.title.ilike('%s%%' % query)).limit(10)
        result = json.dumps((query, [(c.title, 0, []) for c in channels.values('title')], {}))
        return Response('window.google.ac.h(%s)' % result, mimetype='text/javascript')
