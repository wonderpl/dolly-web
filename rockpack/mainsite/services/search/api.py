import re
from flask import request, jsonify
from rockpack.mainsite.core.webservice import WebService, expose
from rockpack.mainsite.core import youtube
from rockpack.mainsite.helpers.db import gen_videoid


SEARCH_TERM_RE = re.compile('^[\w ]+$')


class SearchAPI(WebService):

    endpoint = '/search'

    default_page_size = 10
    max_page_size = 50

    @expose('/video', methods=('GET',))
    def search_videos(self):
        """Search youtube videos."""
        query = request.args.get('q', '')
        if not SEARCH_TERM_RE.match(query):
            query = ''
        start, size = self.get_page()
        region = self.get_locale().split('-')[1]
        result = youtube.search(query, start, size, region, request.remote_addr)
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
