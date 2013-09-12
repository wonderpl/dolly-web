from flask import request, json, abort, Response
from urllib2 import HTTPError
from requests.exceptions import RequestException
from rockpack.mainsite import app
from rockpack.mainsite.core.webservice import WebService, expose_ajax
from rockpack.mainsite.core import youtube
from rockpack.mainsite.helpers.db import gen_videoid
from rockpack.mainsite.services.video.api import get_db_channels
from rockpack.mainsite.services.video.models import Channel, User
from rockpack.mainsite.core.es.api import ChannelSearch, VideoSearch, UserSearch
from rockpack.mainsite.core.es import use_elasticsearch, filters


VIDEO_INSTANCE_PREFIX = 'Svi0xYzZY'


class SearchWS(WebService):

    endpoint = '/search'

    default_page_size = 10
    max_page_size = 50

    @expose_ajax('/videos/', cache_age=3600)
    def search_videos(self):
        """Search youtube videos."""
        order = 'published' if request.args.get('order') == 'latest' else None
        start, size = self.get_page()
        region = self.get_locale().split('-')[1]

        items = []
        query = request.args.get('q', '')
        try:
            result = youtube.search(query, order, start, size,
                                    region, request.remote_addr)
        except (HTTPError, RequestException):
            if not app.config.get('ELASTICSEARCH_URL'):
                raise

            app.logger.exception('Error contacting YouTube: %s', query)

            vs = VideoSearch(self.get_locale())
            vs.add_term('title', query)
            start, size = self.get_page()
            vs.set_paging(offset=start, limit=size)
            for video in vs.videos():
                video['video']['source_view_count'] = video['video']['view_count']
                video['video']['source_date_uploaded'] = video['date_added']
                del video['video']['star_count']
                del video['public']
                del video['category']
                del video['video']['view_count']
                del video['date_added']
                items.append(video)
            total = vs.total
        else:
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
            total = result.video_count

        return {'videos': {'items': items, 'total': total}}

    @expose_ajax('/channels/', cache_age=900)
    def search_channels(self):
        if use_elasticsearch():
            ch = ChannelSearch(self.get_locale())
            offset, limit = self.get_page()
            ch.set_paging(offset, limit)
            ch.search_terms(request.args.get('q', ''))
            ch.add_filter(filters.verified_channel_boost())
            ch.add_filter(filters.negatively_boost_favourites())
            if request.args.get('order') == 'latest':
                ch.date_sort('desc')
            items, total = ch.channels(with_owners=True), ch.total
        else:
            # DB fallback
            date_order = True if request.args.get('order') == 'latest' else False
            items, total = get_db_channels(self.get_locale(),
                                           self.get_page(),
                                           query=request.args.get('q', ''),
                                           date_order=date_order)
        return dict(channels=dict(items=items, total=total))

    @expose_ajax('/users/', cache_age=300)
    def search_users(self):
        search_term = request.args.get('q', '').lower()
        offset, limit = self.get_page()
        if use_elasticsearch():
            us = UserSearch()
            us.set_paging(offset, limit)
            us.add_text('username', search_term)
            us.add_text('display_name', search_term)
            return dict(users=dict(items=us.users(), total=us.total))

        users = User.query.filter(User.username.ilike(search_term))
        count = users.count()
        items = []
        for user in users.limit(limit).offset(offset):
            items.append(
                dict(
                    id=user.id,
                    username=user.username,
                    display_name=user.display_name,
                    avatar_thumbnail_url=user.avatar.url,
                    resource_url=user.resource_url
                )
            )
        return dict(users=dict(items=items, total=count))


class CompleteWS(WebService):

    endpoint = '/complete'

    @expose_ajax('/videos/', cache_age=86400)
    def complete_video_terms(self):
        # Client should hit youtube service directly because this service
        # is likely to be throttled by IP address
        query = request.args.get('q', '')
        if not query:
            abort(400)
        result = youtube.complete(query)
        if len(query) >= app.config.get('USE_CHANNEL_TERMS_FOR_VIDEO_COMPLETE', 4):
            try:
                result = result.decode('utf8')
            except UnicodeDecodeError:
                result = result.decode('latin1')
            terms = json.loads(result[result.index('(') + 1:result.rindex(')')])
            return self.complete_channel_terms(terms[1])
        return Response(result, mimetype='text/javascript')

    @expose_ajax('/channels/', cache_age=86400)
    def complete_channel_terms(self, extra_terms=None):
        # Use same javascript format as google complete for the sake of
        # consistency with /complete/videos
        query = request.args.get('q', '')

        username_terms = list(
            User.query.filter(User.username.ilike('%s%%' % query)).
            filter_by(is_active=True).
            join(Channel).group_by(User.id).
            order_by('count(*) desc').limit(10).values('username'))

        channel_terms = list(
            Channel.query.filter(Channel.title.ilike('%s%%' % query)).
            filter_by(deleted=False, public=True, visible=True).
            order_by('subscriber_count desc').limit(10).values('title'))

        # For each term source, add up to 3 at the top and then fill with
        # remaining sources, if any
        terms = []
        i = 0
        for src in username_terms, channel_terms, extra_terms:
            if src:
                c = max(i, 10 - len(src))
                terms = terms[:c] + src[:10 - min(c, len(terms))]
                i += 3

        result = json.dumps((query, [(t[0], 0, []) for t in terms], {}))
        return Response('window.google.ac.h(%s)' % result, mimetype='text/javascript')
