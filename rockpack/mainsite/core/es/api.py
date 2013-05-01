from urlparse import urlparse, urljoin
import pyes
from . import mappings
from . import es_connection
from . import exceptions
from . import filters
from rockpack.mainsite import app
from rockpack.mainsite.helpers.urls import url_for


DEFAULT_FILTERS = [filters.locale_filter]

# Term occurance conditions
MUST = 'must'
MUST_NOT = 'must_not'
SHOULD = 'shoud'


class CategoryMixin(object):
    """ Provides `filter_category` method to restrict
        queries to a specific category
        
        Assumes a top-level category field """

    def filter_category(self, category):
        if category:
            self.add_term('category', category)


class EntitySearch(object):
    """ Uses elasticsearch """

    def __init__(self, entity, locale=None):
        self._conn = es_connection
        self.entity = entity
        self.locale = locale
        self.ids = []
        self.paging = (0, 100)  # default paging

        self._filters = []

        self._must_terms = []
        self._should_terms = []
        self._must_not_terms =[]

        self._query_params = {}
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
            if isinstance(f, list):
                self._filters += f
            else:
                self._filters.append(f)

    def _construct_terms(self):
        if self._must_terms or self._should_terms or self._must_not_terms:
            return pyes.BoolQuery(must=self._must_terms, must_not=self._must_not_terms, should=self._should_terms)
        return pyes.MatchAllQuery()

    def _construct_filters(self, query):
        """ Wraps a query to apply score filters to """
        if self._filters:
            return pyes.CustomFiltersScoreQuery(query, self._filters)
        return query

    def _construct_query(self):
        self._apply_default_filters()
        query = self._construct_terms()
        query = self._construct_filters(query)
        return query

    def _update_query_params(self, dict_):
        if dict_:
            self.query_params.update(dict_)

    def _es_search(self):
        query = self._construct_query()
        search_query = pyes.Search(query, start=self.paging[0], size=self.paging[1])
        return self._conn.search(
            query=search_query,
            indices=self.get_index_name(),
            doc_types=self.get_type_name(),
            **self._query_params)

    def get_index_name(self):
        return getattr(mappings, self.entity.upper() + '_INDEX')

    def get_type_name(self):
        return getattr(mappings, self.entity.upper() + '_TYPE')

    def add_id(self, id):
        """ IDs of the documents to be queried """
        self._add_term_occurs(pyes.IdsQuery(id), MUST)

    def add_term(self, field, value, occurs=MUST):
        """ Condition to apply

            field  - field name
            value  - some value
            occurs - query constraint (MUST, MUST_NOT, OR SHOULD) """

        term = pyes.TermsQuery if isinstance(value, list) else pyes.TermQuery
        self._add_term_occurs(term, occurs)

    def add_filter(self, filter_):
        self._filters.append(filter_)

    def add_sort(self, sort):
        sort_string = self._query_params.get('sort', sort)
        if sort_string != sort:
            sort_string = ','.join([sort_string, sort])
        self._update_query_params({'sort': self.sorting})

    def set_paging(self, offset=0, limit=100):
        self.paging = (offset, limit)

    def results(self, force=False):
        if self._results and not force:
            return self._results
        self._results = self._es_search()
        return self._results


    def add_ids(self, ids):
        if isinstance(ids, (list, set)):
            self._ids += list(ids)
        else:
            self._ids.append(list(ids))

    @property
    def sorting(self):
        if not self._sorting:
            return None
        return ','.join(self._sorting)

    @property
    def total(self):
        if not self._results:
            return None
        return self._results.total




class ChannelSearch(EntitySearch, CategoryMixin):

    def __init__(self, locale):
        super(ChannelSearch, self).__init__('channel', locale)
        self._category = None
        self._channel_results = None

    @classmethod
    def add_owner_to_channels(cls, channels, owners):
        for channel in channels:
            channel['owner'] = owners[channel['owner']]

    def _format_results(self, channels, with_owners=False):
        channel_list = []
        owner_list = []
        for pos, channel in enumerate(channels):
            ch = dict(
                id=channel.id,
                owner=channel.owner,
                category=channel.category,
                subscriber_count=channel.subscriber_count,
                description=channel.description,
                title=channel.title,
                public=channel.public,
                favourite=channel.favourite,
                position=pos
            )

            for k, v in channel.iteritems():
                if isinstance(v, (str, unicode)) and k.endswith('_url'):
                    url = v
                    if k == 'resource_url':
                        url = urljoin(url_for('basews.discover'), v)
                    elif k != 'ecommerce_url':
                        url = urljoin(app.config.get('IMAGE_CDN', ''), v)
                    ch[k] = url
                # XXX: tis a bit dangerous to assume max(cat)
                # is the child category. review this
                if k == 'category':
                    ch[k] = max(channel[k]) if channel[k] and isinstance(channel[k], list) else channel[k]

            channel_list.append(ch)
            if with_owners:
                owner_list.append(channel['owner'])

        if with_owners:
            ows = OwnerSearch()
            ows.set_paging(limit=len(channels))
            ows.add_id(owner_list)
            owner_map = {owner['id']: owner for owner in ows.owners()}
            self.add_owner_to_channels(channel_list, owner_map)
        return channel_list

    def channels(self, with_owners=True, with_videos=False):
        if not self._channel_results:
            r = self.results()
            self._channel_results = self._format_results(r, with_owners=with_owners)
        return self._channel_results


class VideoSearch(EntitySearch, CategoryMixin):
    pass


class OwnerSearch(EntitySearch):
    def __init__(self):
        super(OwnerSearch, self).__init__('user')
        self._owner_results = None

    def _format_results(self, owners):
        owner_list = []
        for owner in owners:
            owner_list.append(
                dict(
                    id=owner.id,
                    username=owner.username,
                    display_name=owner.display_name,
                    avatar_thumbnail_url=urljoin(app.config.get('IMAGE_CDN', ''), owner.avatar_thumbnail_url)
                )
            )
        return owner_list

    def owners(self, with_channels=False):
        if not self._owner_results:
            self._owner_results = self._format_results(self.results())
        return self._owner_results


class IndexSearch(object):
    def __init__(self, prefix, locale):
        if prefix.lower() not in ('channel', 'video', 'user'):
            raise exceptions.InvalidSearchIndexPrefix(prefix)

        self.conn = es_connection
        self.locale = locale
        self.index_name = prefix.upper() + '_INDEX'
        self.type_name = prefix.upper() + '_TYPE'

        self.terms = []
        self.filters = []

        # apply default filters
        self._locale_filters()

    def _locale_filters(self):
        """ Prioritises results for a given locale.

            For the current locale, apply a boost factor where the view_count
            is higher than another locale. This should result in relevant documents
            for this locale rising to the top (showing all results, but prioritising
            this locale). """
        if not self.locale:
            return []

        filters = []
        for el in app.config.get('ENABLED_LOCALES'):
            if self.locale != el:
                # NOTE: This might get unwieldy for a large number of locales,
                # Need to find a better way of doing this
                script = "doc['locale.{}.view_count'].value > doc['locale.{}.view_count'].value ? 1 : 0".format(self.locale, el)
                filters.append(pyes.CustomFiltersScoreQuery.Filter(pyes.ScriptFilter(script=script), 5.0))
        self.filters += filters

    def add_term(self, field, value):
        """ Field or fields to perform a query against,
            and the value to be queried """
        # TODO: field should use dot notation. Need to test.
        f = pyes.TermsQuery if isinstance(value, list) else pyes.TermQuery
        self.terms.append(f(field=field, value=value))

    def add_ids(self, ids):
        """ IDs of the documents to be queried """
        self.terms.append(pyes.IdsQuery(ids))

    def add_filter(self, filter_):
        """ Add a pyes filter object """
        self.filters.append(filter_)

    def _apply_all(self):
        """ Apply all filters and queries
            and return final query """

        query = pyes.MatchAllQuery()
        if self.terms:
            query = self.terms[0] if len(self.terms) == 1 else pyes.BoolQuery(must=self.terms)
        if self.filters:
            query = pyes.CustomFiltersScoreQuery(query, self.filters)
        return query

    def search(self, start=None, limit=None, sort=''):
        search_kwargs = {}
        if start is not None and limit is not None:
            search_kwargs.update({'start': start, 'size': limit})
        return self.conn.search(
            query=pyes.Search(self._apply_all(), **search_kwargs),
            indices=getattr(mappings, self.index_name),
            doc_types=[getattr(mappings, self.type_name)],
            sort=sort)


class CustomScoreFilters:

    @staticmethod
    def verified_channel_boost():
        return pyes.CustomFiltersScoreQuery.Filter(
            pyes.TermFilter(field='verified', value=True, boost=1.5)
        )

    @staticmethod
    def editorial_boost():
        return pyes.CustomFiltersScoreQuery.Filter(
            pyes.TermFilter(script="_score * doc['editorial_boost'].value")
        )


def add_to_index(data, index, _type, id, bulk=False, refresh=False):
    try:
        es_connection.index(data, index, _type, id=id, bulk=bulk)
    except Exception as e:
        app.logger.critical("Failed to insert record to index '{}' with id '{}' with: {}".format(index, id, str(e)))
    else:
        if refresh or app.config.get('FORCE_INDEX_INSERT_REFRESH', False):
            es_connection.indices.refresh(index)


def add_owner_to_index(owner, bulk=False, refresh=False):
    i = add_to_index(
        {
            'id': owner['id'],
            'avatar_thumbnail': owner['avatar_thumbnail'],
            'resource_url': owner['resource_url'],
            'display_name': owner['display_name'],
            'username': owner['username']
        },
        mappings.USER_INDEX,
        mappings.USER_TYPE,
        id=owner['id'],
        bulk=bulk,
        refresh=refresh)
    return i


def add_channel_to_index(channel, bulk=False, refresh=False, boost=None):
    data = {
        'id': channel['id'],
        'public': True,  # we assume we dont insert private/invisible
        'locale': channel['locale'],
        'ecommerce_url': channel['ecommerce_url'],
        'subscriber_count': channel['subscriber_count'],
        'category': channel['category'],
        'description': channel['description'],
        'thumbnail_url': urlparse(channel['thumbnail_url']).path,
        'cover_thumbnail_small_url': urlparse(channel['cover_thumbnail_small_url']).path,
        'cover_thumbnail_large_url': urlparse(channel['cover_thumbnail_large_url']).path,
        'cover_background_url': urlparse(channel['cover_background_url']).path,
        'resource_url': urlparse(channel['resource_url']).path,
        'title': channel['title'],
        'date_added': channel['date_added'],
        'owner': channel['owner_id'],
        'favourite': channel['favourite'],
        'verified': channel['verified'],
    }
    if boost:
        data['_boost'] = boost

    i = add_to_index(data, mappings.CHANNEL_INDEX, mappings.CHANNEL_TYPE, id=channel['id'], bulk=bulk, refresh=refresh)
    return i


def add_video_to_index(video_instance, bulk=False, refresh=False):
    i = add_to_index(
        {
            'id': video_instance['id'],
            'public': True,  # we assume we dont insert private/invisible
            'locale': video_instance['locale'],
            'channel': video_instance['channel'],
            'category': video_instance['category'],
            'title': video_instance['title'],
            'date_added': video_instance['date_added'],
            'position': video_instance['position'],
            'video': {
                'id': video_instance['video_id'],
                'thumbnail_url': video_instance['thumbnail_url'],
                'source': video_instance['source'],
                'source_id': video_instance['source_id'],
                'source_username': video_instance['source_username'],
                'duration': video_instance['duration'],
            }
        },
        mappings.VIDEO_INDEX,
        mappings.VIDEO_TYPE,
        id=video_instance['id'],
        bulk=bulk,
        refresh=refresh)
    return i


def remove_channel_from_index(channel_id):
    conn = es_connection
    try:
        conn.delete(mappings.CHANNEL_INDEX, mappings.CHANNEL_TYPE, channel_id)
    except pyes.exceptions.NotFoundException:
        app.logger.warning("Failed to remove channel '{}' from index".format(channel_id))


def remove_video_from_index(video_id):
    conn = es_connection
    try:
        conn.delete(mappings.VIDEO_INDEX, mappings.VIDEO_TYPE, video_id)
    except pyes.exceptions.NotFoundException:
        app.logger.warning("Failed to remove video '{}' from index".format(video_id))
