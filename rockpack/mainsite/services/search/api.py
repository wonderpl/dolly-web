import re
import pyes
from functools import wraps
from flask import request, json, abort, Response
from sqlalchemy import func
from urllib2 import HTTPError
from werkzeug.datastructures import ImmutableMultiDict
from requests.exceptions import RequestException
from rockpack.mainsite import app
from rockpack.mainsite.core.webservice import WebService, expose_ajax
from rockpack.mainsite.core import youtube
from rockpack.mainsite.helpers.db import gen_videoid
from rockpack.mainsite.services.video.api import get_db_channels
from rockpack.mainsite.services.video.models import Channel, User
from rockpack.mainsite.core.es import use_elasticsearch, filters
from rockpack.mainsite.core.es.search import (
    ChannelSearch, VideoSearch, UserSearch, SuggestionSearch, MUST)


VIDEO_INSTANCE_PREFIX = 'Svi0xYzZY'

# lucene special characters
sub_string = lambda x: re.sub(r'([\/\+\-\&\|\!\(\)\{\}\[\]\^\"\~\*\?\:\\])', r'\\\1', x)


def escape_and_retry(func):
    """ Modifies request.args.get('q') and retries func
        if pyes.exceptions.ElasticSearchException is thrown

        WARNING: yes, this does indeed modify request.args
        in order to escape any special characters in the query phrase
        so handle with care --- may cause paralysis or death """
    @wraps(func)
    def wrapper(*args, **kwargs):
        for retry in 0, 1:
            try:
                return func(*args, **kwargs)
            except pyes.exceptions.ElasticSearchException:
                if retry:
                    raise

                # request.args is immutable so ...
                d = dict(request.args)

                # sanitise the query
                d['q'] = sub_string(request.args.get('q', '')).lower()

                # put everything back how it (mostly) was
                request.args = ImmutableMultiDict(d)
    return wrapper


class SearchWS(WebService):

    endpoint = '/search'

    default_page_size = 10
    max_page_size = 50

    @expose_ajax('/videos/', cache_age=3600)
    @escape_and_retry
    def search_videos(self):
        """Search youtube videos."""
        def _add_tracking(item, extra=None):
            item['tracking_code'] = 'video-search %d' % item['position']

        order = 'published' if request.args.get('order') == 'latest' else None
        start, size = self.get_page()
        region = self.get_locale().split('-')[1]

        def _search_es(query):
            vs = VideoSearch(self.get_locale())
            # Split the term so that the search phrase is
            # over each individual word, and not the phrase
            # as a whole - the index will have tokenised
            # each word and without splitting we won't get
            # any results back (standard indexer on video title)
            if not app.config.get('DOLLY'):
                vs.add_term('title', query.split())
            else:
                # Snowball analyzer is on the Dolly mapping
                # so we can do a proper search here
                vs.search_terms(sub_string(query))
                vs.add_term('most_influential', True, occurs=MUST)
                # also clear any favs from search
            start, size = self.get_page()
            vs.set_paging(offset=start, limit=size)
            total = vs.total
            return total, vs.videos(add_tracking=_add_tracking)

        items = []
        query = request.args.get('q', '')

        if app.config.get('DOLLY', False) and not request.args.get('source', '').lower() == 'youtube':
            # Only search within the platform
            total, items = _search_es(query)
        else:
            try:
                result = youtube.search(query, order, start, size,
                                        region, request.remote_addr)
            except (HTTPError, RequestException):
                if not app.config.get('ELASTICSEARCH_URL'):
                    raise

                app.logger.exception('Error contacting YouTube: %s', query)
                total, items = _search_es(query)
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
    @escape_and_retry
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
    @escape_and_retry
    def search_users(self):
        def _add_tracking(item, extra=None):
            item['tracking_code'] = 'user-search %d' % item['position']

        search_term = request.args.get('q', '').lower()
        offset, limit = self.get_page()
        if use_elasticsearch():
            us = UserSearch()
            us.set_paging(offset, limit)
            if app.config.get('DOLLY'):
                us.search_terms(search_term)
            else:
                us.add_text('username', search_term)
                us.add_text('display_name', search_term)
            items = us.users(add_tracking=_add_tracking)
            return dict(users=dict(items=items, total=us.total))

        users = User.query.filter(func.lower(User.username).like(search_term))
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

    @expose_ajax('/all/', cache_age=86400)
    def complete_all_terms(self):
        query = request.args.get('q', '')
        if not query:
            abort(400)
        if app.config.get('DOLLY') and use_elasticsearch():
            terms = SuggestionSearch().completion_suggestions(query)
            result = json.dumps((query, [(t, 0) for t in terms], {}))
            return Response('window.google.ac.h(%s)' % result, mimetype='text/javascript')
        result = youtube.complete(query)
        if len(query) >= 4:
            try:
                result = result.decode('utf8')
            except UnicodeDecodeError:
                result = result.decode('latin1')
            terms = json.loads(result[result.index('(') + 1:result.rindex(')')])
            return self.complete_channel_terms(terms[1])
        return Response(result, mimetype='text/javascript')

    @expose_ajax('/videos/', cache_age=86400)
    def complete_video_terms(self, all=False):
        if app.config.get('USE_ALL_TERMS_FOR_VIDEO_COMPLETE', False):
            return self.complete_all_terms()
        # Client should hit youtube service directly because this service
        # is likely to be throttled by IP address
        query = request.args.get('q', '')
        if not query:
            abort(400)
        result = youtube.complete(query)
        return Response(result, mimetype='text/javascript')

    @expose_ajax('/channels/', cache_age=86400)
    def complete_channel_terms(self, extra_terms=None):
        # Use same javascript format as google complete for the sake of
        # consistency with /complete/videos
        query = request.args.get('q', '').lower()

        username_terms = [
            (uname, ('user', uid, uname, avatar.url))
            for uid, uname, avatar in
            User.query.filter(func.lower(User.username).like('%s%%' % query)).
            filter_by(is_active=True).
            join(Channel).group_by(User.id).
            order_by('count(*) desc').limit(10).values(User.id, User.username, User.avatar)
        ]

        channel_terms = [
            (title, ('channel', cid)) for cid, title in
            Channel.query.filter(func.lower(Channel.title).like('%s%%' % query)).
            filter_by(deleted=False, public=True, visible=True).
            order_by('subscriber_count desc').limit(10).values(Channel.id, 'title')
        ]

        # For each term source, add up to 3 at the top and then fill with
        # remaining sources, if any
        terms = []
        i = 0
        for src in username_terms, channel_terms, extra_terms:
            if src:
                c = max(i, 10 - len(src))
                terms = terms[:c] + src[:10 - min(c, len(terms))]
                i += 3

        result = json.dumps((query, [(t[0], t[1]) for t in terms], {}))
        return Response('window.google.ac.h(%s)' % result, mimetype='text/javascript')

    @expose_ajax('/users/', cache_age=86400)
    def complete_user_terms(self, extra_terms=None):
        query = request.args.get('q', '').lower()

        terms = set(
            next((n for n in names if n.lower().startswith(query)), names[0])
            for names in
            User.query.filter_by(is_active=True).filter(
                func.lower(User.username).like('%s%%' % query) |
                func.lower(User.first_name).like('%s%%' % query) |
                func.lower(User.last_name).like('%s%%' % query)
            ).join(Channel).group_by(User.id).
            order_by('count(*) desc').limit(10).
            values('username', 'first_name', 'last_name')
        )

        result = json.dumps((query, [(t, 0) for t in terms], {}))
        return Response('window.google.ac.h(%s)' % result, mimetype='text/javascript')
