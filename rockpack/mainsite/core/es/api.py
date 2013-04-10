import pyes
from . import mappings
from rockpack.mainsite import app


class InvalidSearchIndexPrefix(Exception):
    pass


class IndexSearch(object):
    def __init__(self, conn, prefix, locale):
        if prefix.lower() not in ('channel', 'video'):
            raise InvalidSearchIndexPrefix(prefix)

        self.conn = conn
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


def add_owner_to_index(conn, owner):
    i = conn.index({
        'id': owner.id,
        'avatar_thumbnail': str(owner.avatar),
        'resource_url': owner.get_resource_url(False),
        'display_name': owner.display_name,
        'name': owner.username},
        mappings.USER_INDEX,
        mappings.USER_TYPE,
        id=owner.id)
    conn.indices.refresh(mappings.USER_INDEX)
    return i


def add_channel_to_index(conn, channel):
    i = conn.index({
        'id': channel['id'],
        'public': True, # we assume we dont insert private/invisible
        'locale': channel['locale'],
        'subscribe_count': channel['subscribe_count'],
        'category': channel['category'],
        'description': channel['description'],
        'thumbnail_url': channel['thumbnail_url'],
        'cover_thumbnail_small_url': channel['cover_thumbnail_small_url'],
        'cover_thumbnail_large_url': channel['cover_thumbnail_large_url'],
        'cover_background_url': channel['cover_background_url'],
        'resource_url': channel['resource_url'],
        'title': channel['title'],
        'date_added': channel['date_added'],
        'owner': channel['owner_id'],
        },
        mappings.CHANNEL_INDEX,
        mappings.CHANNEL_TYPE,
        id=channel['id'])
    conn.indices.refresh(mappings.CHANNEL_INDEX)
    return i


def add_video_to_index(conn, video_instance):
    return conn.index({
        'id': video_instance['id'],
        'public': True, # we assume we dont insert private/invisible
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
            'duration': video_instance['duration'],
            }
        },
        mappings.VIDEO_INDEX,
        mappings.VIDEO_TYPE,
        id=video_instance['id'])


def remove_channel_from_index(conn, channel_id):
    try:
        print conn.delete(mappings.CHANNEL_INDEX, mappings.CHANNEL_TYPE, channel_id)
    except pyes.exceptions.NotFoundException:
        pass


def remove_video_from_index(conn, video_id):
    try:
        print conn.delete(mappings.VIDEO_INDEX, mappings.VIDEO_TYPE, video_id)
    except pyes.exceptions.NotFoundException:
        pass
