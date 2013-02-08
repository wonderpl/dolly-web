import re
from flask import request, jsonify, json, Response, g
from rockpack.mainsite.core.webservice import WebService, expose
from rockpack.mainsite.core import youtube
from rockpack.mainsite.helpers.db import gen_videoid
from rockpack.mainsite.helpers.http import cache_for
from rockpack.mainsite.services.video.api import get_local_channel
from rockpack.mainsite.services.video.models import Channel


SEARCH_TERM_RE = re.compile('^[\w ]+$')


def _query_term(default=''):
    query = request.args.get('q', '')
    return query if SEARCH_TERM_RE.match(query) else default


class SearchAPI(WebService):

    endpoint = '/search'

    default_page_size = 10
    max_page_size = 50

    @expose('/videos', methods=('GET',))
    @cache_for(seconds=300)
    def search_videos(self):
        """Search youtube videos."""
        start, size = self.get_page()
        region = self.get_locale().split('-')[1]
        result = youtube.search(_query_term(), start, size,
                                region, request.remote_addr)
        items = []
        for position, video in enumerate(result.videos, start):
            items.append(
                dict(
                    position=position,
                    id=gen_videoid(None, 1, video.source_videoid),
                    source=1,
                    source_id=video.source_videoid,
                    thumbnail_url=video.default_thumbnail,
                )
            )
        return jsonify({'videos': {'items': items, 'total': result.video_count}})

    @expose('/channels', methods=('GET',))
    @cache_for(seconds=300)
    def search_channels(self):
        # XXX: Obviously this needs to be replaced by a search engine
        items, total = get_local_channel(self.get_locale(),
                                         self.get_page(),
                                         query=_query_term())
        return jsonify({'channels': {'items': items, 'total': total}})


class CompleteAPI(WebService):

    endpoint = '/complete'

    @expose('/videos', methods=('GET',))
    @cache_for(seconds=3600)
    def complete_video_terms(self):
        # Client should hit youtube service directly because this service
        # is likely to be throttled by IP address
        result = youtube.complete(_query_term())
        return Response(result, mimetype='text/javascript')

    @expose('/channels', methods=('GET',))
    @cache_for(seconds=3600)
    def complete_channel_terms(self):
        # Use same javascript format as google complete for the sake of
        # consistency with /complete/videos
        query = _query_term()
        terms = g.session.query(Channel.title).\
            filter(Channel.title.ilike('%s%%' % query)).limit(10)
        result = json.dumps((query, [(t.title, 0, []) for t in terms], {}))
        return Response('window.google.ac.h(%s)' % result, mimetype='text/javascript')
