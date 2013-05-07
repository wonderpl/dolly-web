from urlparse import urlparse
import pyes
from . import mappings
from . import es_connection
from rockpack.mainsite import app


class InvalidSearchIndexPrefix(Exception):
    pass


class IndexSearch(object):
    def __init__(self, prefix, locale):
        if prefix.lower() not in ('channel', 'video', 'user'):
            raise InvalidSearchIndexPrefix(prefix)

        self.conn = es_connection
        self.locale = locale
        self.index_name = prefix.upper() + '_INDEX'
        self.type_name = prefix.upper() + '_TYPE'

        self.terms = []

    def _locale_filters(self, locale):
        if not locale:
            return []

        filters = []
        for el in app.config.get('ENABLED_LOCALES'):
            if locale != el:
                script = "doc['locale.{}.view_count'].value > doc['locale.{}.view_count'].value ? 1 : 0".format(locale, el)
                filters.append(pyes.CustomFiltersScoreQuery.Filter(pyes.ScriptFilter(script=script), 5.0))
        return filters

    def add_term(self, field, value):
        # TODO: field should use dot notation. Need to test.
        f = pyes.TermsQuery if isinstance(value, list) else pyes.TermQuery
        self.terms.append(f(field=field, value=value))

    def add_ids(self, ids):
        self.terms.append(pyes.IdsQuery(ids))

    def _get_terms_query(self):
        if not self.terms:
            return pyes.MatchAllQuery()
        return self.terms[0] if len(self.terms) == 1 else pyes.BoolQuery(must=self.terms)

    def _get_filters_query(self, q):
        if not self.locale:
            return q
        filters = self._locale_filters(self.locale)
        return pyes.CustomFiltersScoreQuery(q, filters)

    def _get_full_query(self):
        q = self._get_terms_query()
        return self._get_filters_query(q)

    def search(self, start=None, limit=None, sort=''):
        search_kwargs = {}
        if start is not None and limit is not None:
            search_kwargs.update({'start': start, 'size': limit})
        return self.conn.search(
            query=pyes.Search(self._get_full_query(), **search_kwargs),
            indices=getattr(mappings, self.index_name),
            doc_types=[getattr(mappings, self.type_name)],
            sort=sort)


def add_to_index(data, index, _type, id, bulk=False):
    try:
        return es_connection.index(data, index, _type, id=id, bulk=bulk)
    except Exception as e:
        app.logger.critical("Failed to insert record to index '{}' with id '{}' with: {}".format(index, id, str(e)))


def add_owner_to_index(owner, bulk=False, refresh=True):
    conn = es_connection
    i = add_to_index(
        {
            'id': owner['id'],
            'avatar_thumbnail': owner['avatar_thumbnail'],
            'resource_url': owner['resource_url'],
            'display_name': owner['display_name'],
            'name': owner['name']
        },
        mappings.USER_INDEX,
        mappings.USER_TYPE,
        id=owner['id'],
        bulk=bulk)
    if refresh:
        conn.indices.refresh(mappings.USER_INDEX)
    return i


def add_channel_to_index(channel, bulk=False, refresh=True):
    conn = es_connection
    i = add_to_index(
        {
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
        },
        mappings.CHANNEL_INDEX,
        mappings.CHANNEL_TYPE,
        id=channel['id'],
        bulk=bulk)
    if refresh:
        conn.indices.refresh(mappings.CHANNEL_INDEX)
    return i


def add_video_to_index(video_instance, bulk=False, refresh=True):
    conn = es_connection
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
        bulk=bulk)
    if refresh:
        conn.indices.refresh(mappings.VIDEO_INDEX)
    return i


def remove_channel_from_index(channel_id):
    conn = es_connection
    try:
        print conn.delete(mappings.CHANNEL_INDEX, mappings.CHANNEL_TYPE, channel_id)
    except pyes.exceptions.NotFoundException:
        pass


def remove_video_from_index(video_id):
    conn = es_connection
    try:
        print conn.delete(mappings.VIDEO_INDEX, mappings.VIDEO_TYPE, video_id)
    except pyes.exceptions.NotFoundException:
        pass
