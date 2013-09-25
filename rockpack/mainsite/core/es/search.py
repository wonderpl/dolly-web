import pyes
from urlparse import urljoin
from . import mappings
from . import es_connection
from . import exceptions
from . import filters
from rockpack.mainsite import app
from rockpack.mainsite.helpers.urls import url_for


DEFAULT_FILTERS = []  # [filters.locale_filter]

# Term occurance conditions
MUST = 'must'
MUST_NOT = 'must_not'
SHOULD = 'shoud'


def _format_datetime(datetime):
    # The datetime argument could be a pre-formatted string or a datetime object
    if hasattr(datetime, 'isoformat'):
        return datetime.isoformat()
    else:
        return datetime


class CategoryMixin(object):
    """ Provides `filter_category` method to restrict
        queries to a specific category

        Assumes a top-level category field """

    def __init__(self, *args, **kwargs):
        super(CategoryMixin).__init__(*args, **kwargs)

    def filter_category(self, category):
        if category:
            self.add_term('category', category)


class MediaSortMixin(object):

    def __init__(self, *args, **kwargs):
        super(MediaSortMixin).__init__(*args, **kwargs)

    def _get_order(self, order):
        if (order != 'desc') and (order != 'asc'):
            return 'desc'
        return order

    def favourite_sort(self, order):
        if order:
            self.add_sort('favourite', self._get_order(order))

    def star_order_sort(self, order):
        if order:
            self.add_sort('star_count', self._get_order(order))


class EntitySearch(object):
    """ Uses elasticsearch """

    def __init__(self, entity, locale=None):
        self._conn = es_connection
        self.entity = entity
        self.locale = locale
        self.ids = []
        self.paging = (0, 100)  # default paging

        self._filters = []
        self._exclusion_filters = []
        self._multiple_field_terms = ()

        self._must_terms = []
        self._should_terms = []
        self._must_not_terms = []

        self._query_params = {"track_scores": True}
        self._sorting = []
        self._results = {}  # cache results

    def _add_term_occurs(self, term, occurs):
        try:
            if occurs == MUST:
                self._must_terms.append(term)
            elif occurs == MUST_NOT:
                self._must_not_terms.append(term)
            elif occurs == SHOULD:
                self._should_terms.append(term)
            else:
                raise exceptions.InvalidTermCondition('{} is not a valid condition'.format(occurs))
        except AttributeError:
            raise exceptions.MissingTermsList('{} does not map to a `terms` list'.format(occurs))

    def _apply_default_filters(self):
        for filter_ in DEFAULT_FILTERS:
            f = filter_(self)
            if f:
                if isinstance(f, list):
                    self._filters += f
                else:
                    self._filters.append(f)

    def _construct_terms(self):
        if self._must_terms or self._should_terms or self._must_not_terms:
            return pyes.BoolQuery(must=self._must_terms, must_not=self._must_not_terms, should=self._should_terms,
                minimum_number_should_match=0)
        return pyes.MatchAllQuery()

    def _construct_filters(self, query):
        """ Wraps a query to apply score filters to """
        if self._filters:
            return pyes.CustomFiltersScoreQuery(query, self._filters, score_mode='multiply')
        return query

    def _construct_exclusion_filters(self, query):
        for f in self._exclusion_filters:
            query = pyes.FilteredQuery(query, f)
        return query

    def _construct_query(self):
        self._apply_default_filters()
        query = self._construct_terms()
        query = self._construct_filters(query)
        query = self._construct_exclusion_filters(query)
        return query

    def _update_query_params(self, dict_):
        if dict_:
            self._query_params.update(dict_)

    def _es_search(self):
        query = self._construct_query()
        search_query = pyes.Search(query, start=self.paging[0], size=self.paging[1])
        explain = False
        if app.config.get('DEBUG'):
            explain = True
        result = self._conn.search(
            query=search_query,
            indices=self.get_index_name(),
            doc_types=self.get_type_name(),
            explain=explain,
            **self._query_params)

        if explain:
            from pprint import pprint as pp
            pp(result.search.serialize())
        return result

    def get_index_name(self):
        return getattr(mappings, self.entity.upper() + '_INDEX')

    def get_type_name(self):
        return getattr(mappings, self.entity.upper() + '_TYPE')

    def add_id(self, id, occurs=MUST):
        """ IDs of the documents to be queried """
        self._add_term_occurs(pyes.IdsQuery(id), occurs)

    def add_text(self, field, value):
        if not(field and value):
            return
        term = pyes.TextQuery(field, value)
        self._add_term_occurs(term, SHOULD)

    def add_term(self, field, value, occurs=SHOULD):
        """ Condition to apply

            field  - field name
            value  - some value
            occurs - query constraint (MUST, MUST_NOT, OR SHOULD) """

        if not (field and value):
            return

        f = pyes.TermsQuery if isinstance(value, list) else pyes.TermQuery
        term_query = f(field=field, value=value)
        self._add_term_occurs(term_query, occurs)

    def add_filter(self, filter_):
        """ Adds a (score) filter which alter the score of a result """
        self._filters.append(filter_)

    def add_script_filter(self, filter_, occurs):
        """ Adds a results filter which decides which results to include """
        self._add_term_occurs(filter_, occurs)

    def add_sort(self, sort, order='desc'):
        sort = ':'.join([sort, order])
        sort_string = self._query_params.get('sort', sort)
        if sort_string != sort:
            sort_string = ','.join([sort_string, sort])
        self._update_query_params({'sort': sort_string})

    def date_sort(self, order):
        if order:
            if (order != 'desc') and (order != 'asc'):
                order = 'desc'
            self.add_sort('date_added', order)

    def set_paging(self, offset=0, limit=100):
        if limit == -1:
            limit = 1000
        self.paging = (int(offset), int(limit))

    def results(self, force=False):
        if self._results and not force:
            return self._results
        self._results = self._es_search()
        return self._results

    @property
    def sorting(self):
        if not self._sorting:
            return None
        return ','.join(self._sorting)

    @property
    def total(self):
        if not self._results:
            return 0
        return self._results.total


class ChannelSearch(EntitySearch, CategoryMixin, MediaSortMixin):

    def __init__(self, locale):
        super(ChannelSearch, self).__init__('channel', locale)
        self._country = None
        self._channel_results = None
        self.promoted_category = None

    @classmethod
    def add_owner_to_channels(cls, channels, owners):
        """ Adds owner information to each channel """
        for channel in channels:
            try:
                channel['owner'] = owners[channel['owner']]
            except TypeError:
                pass

    @classmethod
    def add_videos_to_channel(cls, channel, videos, total):
        """ Adds video information to each channel """
        channel.setdefault('videos', {}).setdefault('items', videos.get(channel['id'], []))
        channel['videos']['total'] = total

    def _format_results(self, channels, with_owners=False, with_videos=False, video_paging=(0, 100, )):
        channel_list = range(self.paging[1])  # We don't know the channel size so default to paging
        channel_id_list = []
        owner_list = set()
        IMAGE_CDN = app.config.get('IMAGE_CDN', '')
        BASE_URL = url_for('basews.discover')

        def _check_position(position, max_check):
            if position > max_check:
                return None

            if not isinstance(channel_list[position], int):
                position += 1
                position = _check_position(position, max_check)
            return position

        position = 0
        for channel in channels:
            ch = dict(
                id=channel.id,
                owner=channel.owner,
                category=channel.category,
                subscriber_count=channel.subscriber_count,
                description=channel.description,
                title=channel.title,
                date_published=_format_datetime(channel.date_published),
                public=channel.public,
                cover=dict(
                    thumbnail_url=urljoin(IMAGE_CDN, channel.cover.thumbnail_url) if channel.cover.thumbnail_url else '',
                    aoi=channel.cover.aoi
                )
            )
            if channel.favourite:
                ch['favourites'] = True
            if channel.verified:
                ch['verified'] = True

            for k, v in channel.iteritems():
                if isinstance(v, (str, unicode)) and k.endswith('_url'):
                    url = v
                    if url:
                        if k == 'resource_url':
                            url = urljoin(BASE_URL, v)
                        elif k != 'ecommerce_url':
                            url = urljoin(IMAGE_CDN, v)
                    ch[k] = url

                if k == 'category':
                    if not channel[k]:
                        ch[k] = None
                    elif isinstance(channel[k], list):
                        ch[k] = int(channel[k][0])  # First item is subcat
                    else:
                        ch[k] = int(channel[k])

            if with_owners:
                owner_list.add(channel.owner)
            if with_videos:
                channel_id_list.append(channel.id)

            # ASSUMPTION: We should have all the promoted channels at the top, so positions of
            # the promoted will already be known by the time we're at the regular channels.
            # (lets also hope this assumption isn't anyones mother)
            if channel.promotion:
                promote_pattern = '|'.join([str(self.locale), str(self.promoted_category)]) + '|'
                # Could be a promoted channel
                # for a different category
                promoted_for_category = False

                for p in channel.promotion:
                    if p.startswith(promote_pattern):
                        promoted_for_category = True
                        locale, category, pos = p.split('|')
                        pos = int(pos) - 1  # position isn't zero indexed, so adjust
                        if pos < self.paging[0]:
                            # Don't include channels where its position
                            # is less than the offset position
                            continue

                        # Calculate new offseted position and assign
                        ch['position'] = pos - self.paging[0]
                        channel_list[ch['position']] = ch

                if promoted_for_category:
                    continue

            position = _check_position(position, self.paging[1] - 1)
            ch['position'] = position + self.paging[0]
            channel_list[position] = ch

            # Start incrementing the counter for
            # non-promoted channels
            position += 1

        # A bug in promotions means that
        # we may have an empty position or so.
        # We usually won't hit this, but it's a
        # shit hack, so fix it.
        if position < len(channel_list):
            new_list = []
            for channel in channel_list:
                if not isinstance(channel, int):
                    new_list.append(channel)
            channel_list = new_list

        if with_owners and owner_list:
            us = UserSearch()
            us.add_id(list(owner_list))
            us.set_paging(0, -1)
            owner_map = {owner['id']: owner for owner in us.users()}
            self.add_owner_to_channels(channel_list, owner_map)

        # XXX: this assumes only 1 channel for now
        # This WILL break if there is more than one channel to get videos for
        # as a single video doesnt reference the channel it belongs to
        if with_videos and channel_id_list:
            vs = VideoSearch(self.locale)
            vs.add_term('channel', channel_id_list)
            vs.add_sort('position', 'asc')
            vs.date_sort('desc')
            vs.add_sort('video.date_published', 'desc')
            if self._country:
                vs.check_country_allowed(self._country)
            vs.set_paging(offset=video_paging[0], limit=video_paging[1])
            video_map = {}
            for v in vs.videos():
                video_map.setdefault(channel_id_list[0], []).append(v)  # HACK: see above
            self.add_videos_to_channel(channel_list[0], video_map, vs.total)
        return channel_list

    def promotion_settings(self, category):
        self.promoted_category = category or 0
        self.add_filter(
            pyes.CustomFiltersScoreQuery.Filter(
                pyes.PrefixFilter(
                    field='promotion',
                    prefix='|'.join([str(self.locale), str(self.promoted_category)])
                ),
                script='1000000000000000000'
            )
        )

    def search_terms(self, phrase):
        if phrase:
            query = pyes.StringQuery(
                phrase,
                default_operator='AND',
                search_fields=['title^10', 'video_terms', 'keywords'],
                analyzer='snowball',
                minimum_should_match=0
            )
            self._add_term_occurs(query, MUST)
            query = pyes.TextQuery(
                'video_terms',
                phrase,
                type='phrase',
                operator='and',
                boost=5
            )
            self._add_term_occurs(query, SHOULD)

    def check_country_allowed(self, country):
        """ Set filter on videos for restricted content
            if applicable """
        if country:
            self._country = country

    def channels(self, with_owners=False, with_videos=False, video_paging=(0, 100,)):
        """ Fetches the results of the query for channels """
        if not self._channel_results:
            r = self.results()
            self._channel_results = self._format_results(r, with_owners=with_owners, with_videos=with_videos, video_paging=video_paging)
        return self._channel_results


class VideoSearch(EntitySearch, CategoryMixin, MediaSortMixin):

    def __init__(self, locale):
        super(VideoSearch, self).__init__('video', locale)
        self._video_results = None

    @classmethod
    def add_channels_to_videos(cls, videos, channels):
        """ Adds channel information to each video """
        for video in videos:
            try:
                video['channel'] = channels[video['channel']]
            except KeyError:
                app.logger.warning("Missing channel '%s' during mapping", video['channel'])

    def _format_results(self, videos, with_channels=True, with_stars=False):
        vlist = []
        channel_list = []

        for pos, v in enumerate(videos, self.paging[0]):
            video = dict(
                id=v.id,
                title=v.title,
                date_added=_format_datetime(v.date_added),
                public=v.public,
                category='',
                video=dict(
                    id=v.video.id,
                    view_count=sum(l['view_count'] for l in v['locales'].values()),
                    star_count=sum(l['star_count'] for l in v['locales'].values()),
                    source=['rockpack', 'youtube'][v.video.source],
                    source_id=v.video.source_id,
                    source_username=v.video.source_username,
                    duration=v.video.duration,
                    thumbnail_url=urljoin(app.config.get('IMAGE_CDN', ''), v.video.thumbnail_url) if v.video.thumbnail_url else '',
                ),
                position=pos
            )
            if with_stars:
                video['recent_user_stars'] = v.get('recent_user_stars', [])
            if v.category:
                video['category'] = max(v.category) if isinstance(v.category, list) else v.category
            if with_channels:
                video['channel'] = v.channel
                channel_list.append(v.channel)
            vlist.append(video)

        if with_channels and channel_list:
            ch = ChannelSearch(self.locale)
            ch.add_id(channel_list)
            channel_map = {c['id']: c for c in ch.channels(with_owners=True)}
            self.add_channels_to_videos(vlist, channel_map)

        return vlist

    def check_country_allowed(self, country):
        """ Checks the allow/deny list for country """
        if country:
            self._exclusion_filters.append(filters.country_restriction(country))

    def videos(self, with_channels=False, with_stars=False):
        if not self._video_results:
            r = self.results()
            self._video_results = self._format_results(r, with_channels=with_channels, with_stars=with_stars)
        return self._video_results


class UserSearch(EntitySearch):
    def __init__(self):
        super(UserSearch, self).__init__('user')
        self._user_results = None

    def _format_results(self, users):
        user_list = []
        IMAGE_CDN = app.config.get('IMAGE_CDN', '')
        BASE_URL = url_for('basews.discover')
        for position, user in enumerate(users, self.paging[0]):
            user_list.append(
                dict(
                    id=user.id,
                    username=user.username,
                    display_name=user.display_name,
                    resource_url=urljoin(BASE_URL, user.resource_url),
                    avatar_thumbnail_url=urljoin(IMAGE_CDN, user.avatar_thumbnail_url) if user.avatar_thumbnail_url else '',
                    position=position
                )
            )
        return user_list

    def users(self):
        if not self._user_results:
            self._user_results = self._format_results(self.results())
        return self._user_results