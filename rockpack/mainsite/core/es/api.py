from urlparse import urlparse, urljoin
import pyes
from . import mappings
from . import es_connection
from . import exceptions
from . import filters
from rockpack.mainsite import app
from rockpack.mainsite.helpers.db import ImageType
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

        self._must_terms = []
        self._should_terms = []
        self._must_not_terms = []

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
            if f:
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
            return pyes.CustomFiltersScoreQuery(query, self._filters, score_mode='total')
        return query

    def _construct_query(self):
        self._apply_default_filters()
        query = self._construct_terms()
        query = self._construct_filters(query)
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
            try:
                result.__dict__
                pp(result.__dict__['hits'])
            except:
                pass
            pp(result.__dict__['query'])
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
        self._filters.append(filter_)

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
            return 0
        return self._results.total


class ChannelSearch(EntitySearch, CategoryMixin, MediaSortMixin):

    def __init__(self, locale):
        super(ChannelSearch, self).__init__('channel', locale)
        self._channel_results = None

    @classmethod
    def add_owner_to_channels(cls, channels, owners):
        for channel in channels:
            channel['owner'] = owners[channel['owner']]

    @classmethod
    def add_videos_to_channel(cls, channel, videos, total):
        channel.setdefault('videos', {}).setdefault('items', videos.get(channel['id'], []))
        channel['videos']['total'] = total

    def _format_results(self, channels, with_owners=False, with_videos=False):
        channel_list = []
        channel_id_list = []
        owner_list = []
        for pos, channel in enumerate(channels, self.paging[0]):
            ch = dict(
                id=channel.id,
                owner=channel.owner,
                category=channel.category,
                subscriber_count=channel.subscriber_count,
                description=channel.description,
                title=channel.title,
                public=channel.public,
                position=pos,
                cover=dict(
                    thumbnail_url=urljoin(app.config.get('IMAGE_CDN', ''), channel.cover.thumbnail_url) if channel.cover.thumbnail_url else '',
                    aoi=channel.cover.aoi
                )
            )
            if channel.favourite:
                ch['favourites'] = True

            for k, v in channel.iteritems():
                if isinstance(v, (str, unicode)) and k.endswith('_url'):
                    url = v
                    if url:
                        if k == 'resource_url':
                            url = urljoin(url_for('basews.discover'), v)
                        elif k != 'ecommerce_url':
                            url = urljoin(app.config.get('IMAGE_CDN', ''), v)
                    ch[k] = url
                # XXX: tis a bit dangerous to assume max(cat)
                # is the child category. review this
                if k == 'category':
                    if not channel[k]:
                        ch[k] = None
                    elif isinstance(channel[k], list):
                        ch[k] = channel[k][0]  # First item is subcat
                    else:
                        ch[k] = channel[k]

            channel_list.append(ch)
            if with_owners:
                owner_list.append(channel.owner)
            if with_videos:
                channel_id_list.append(channel.id)

        if with_owners and owner_list:
            ows = OwnerSearch()
            ows.add_id(owner_list)
            ows.set_paging(0, -1)
            owner_map = {owner['id']: owner for owner in ows.owners()}
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
            vs.set_paging(offset=self.paging[0], limit=self.paging[1])
            video_map = {}
            for v in vs.videos():
                video_map.setdefault(channel_id_list[0], []).append(v) # HACK: see above
            self.add_videos_to_channel(channel_list[0], video_map, vs.total)
        return channel_list

    def channels(self, with_owners=False, with_videos=False):
        if not self._channel_results:
            r = self.results()
            self._channel_results = self._format_results(r, with_owners=with_owners, with_videos=with_videos)
        return self._channel_results


class VideoSearch(EntitySearch, CategoryMixin, MediaSortMixin):

    def __init__(self, locale):
        super(VideoSearch, self).__init__('video', locale)
        self._video_results = None

    @classmethod
    def add_channels_to_videos(cls, videos, channels):
        for video in videos:
            try:
                video['channel'] = channels[video['channel']]
            except KeyError:
                app.logger.warning("Missing channel '{}' during mapping".format(video['channel']))

    def _format_results(self, videos, with_channels=True):
        vlist = []
        channel_list = []

        for pos, v in enumerate(videos, self.paging[0]):
            video = dict(
                id=v.id,
                title=v.title,
                # XXX: should return either datetime or isoformat - something is broken
                date_added=v.date_added.isoformat() if not isinstance(v.date_added, (str, unicode)) else v.date_added,
                public=v.public,
                category='',
                video=dict(
                    id=v.video.id,
                    view_count=v['locales'][self.locale]['view_count'],
                    star_count=v['locales'][self.locale]['star_count'],
                    source=['rockpack', 'youtube'][v.video.source],
                    source_id=v.video.source_id,
                    duration=v.video.duration,
                    thumbnail_url=urljoin(app.config.get('IMAGE_CDN', ''), v.video.thumbnail_url) if v.video.thumbnail_url else '',
                ),
                position=pos
            )
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

    def videos(self, with_channels=False):
        if not self._video_results:
            r = self.results()
            self._video_results = self._format_results(r, with_channels=with_channels)
        return self._video_results


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
                    resource_url=urljoin(url_for('basews.discover'), owner.resource_url),
                    avatar_thumbnail_url=urljoin(app.config.get('IMAGE_CDN', ''), owner.avatar_thumbnail_url) if owner.avatar_thumbnail_url else ''
                )
            )
        return owner_list

    def owners(self):
        if not self._owner_results:
            self._owner_results = self._format_results(self.results())
        return self._owner_results


def add_to_index(data, index, _type, id, bulk=False, refresh=False):
    try:
        return es_connection.index(data, index, _type, id=id, bulk=bulk)
    except Exception as e:
        app.logger.critical("Failed to insert record to index '{}' with id '{}' with: {}".format(index, id, str(e)))
    else:
        if refresh or app.config.get('FORCE_INDEX_INSERT_REFRESH', False):
            es_connection.indices.refresh(index)


def locale_dict_from_object(metas):
    locales = {el: {} for el in app.config.get('ENABLED_LOCALES')}
    meta_dict = {m.locale: m for m in metas}
    for loc in locales.keys():
        meta = meta_dict.get(loc)
        locales[loc] = {
            'view_count': getattr(meta, 'view_count', 0),
            'star_count': getattr(meta, 'star_count', 0)
        }
    return locales


def convert(obj, attr, type_):
    obj_attr = getattr(obj, attr)
    if isinstance(obj_attr, (str, unicode)):
        return ImageType(type_).process_result_value(obj_attr, None)
    return obj_attr


def check_es(no_check=False):
    if not no_check:
        if not app.config.get('ELASTICSEARCH_URL', False):
            return False
    return True


def add_owner_to_index(owner, bulk=False, refresh=False, no_check=False):
    if not check_es(no_check):
        return

    data = dict(
        id=owner.id,
        avatar_thumbnail_url=urlparse(convert(owner, 'avatar', 'AVATAR').thumbnail_small).path,
        resource_url=urlparse(owner.resource_url).path,
        display_name=owner.display_name,
        username=owner.username
    )
    return add_to_index(data, mappings.USER_INDEX, mappings.USER_TYPE, id=owner.id, bulk=bulk, refresh=refresh)


def add_channel_to_index(channel, bulk=False, refresh=False, boost=None, no_check=False):
    if not check_es(no_check):
        return

    category = []
    if channel.category:
        if not channel.category_rel:
            # Avoid circular import
            from rockpack.mainsite.services.video.models import Category
            category = Category.query.filter_by(id=channel.category).values('id', 'parent').next()
        else:
            category = [channel.category_rel.id, channel.category_rel.parent]

    data = dict(
        id=channel.id,
        public=channel.public,
        category=category,
        locales=locale_dict_from_object(channel.metas),
        owner=channel.owner,
        subscriber_count=channel.subscriber_count,
        date_added=channel.date_added,
        date_updated=channel.date_updated,
        description=channel.description,
        resource_url=urlparse(channel.get_resource_url()).path,
        title=channel.title,
        ecommerce_url=channel.ecommerce_url,
        favourite=channel.favourite,
        verified=channel.verified,
        update_frequency=channel.update_frequency,
        editorial_boost=channel.editorial_boost,
        cover=dict(
            thumbnail_url=urlparse(convert(channel, 'cover', 'CHANNEL').url).path,
            aoi=channel.cover_aoi
        ),
        keywords=[channel.owner_rel.display_name.lower(), channel.owner_rel.username.lower()]
    )

    if app.config.get('SHOW_OLD_CHANNEL_COVER_URLS', True):
        for k in 'thumbnail_large', 'thumbnail_small', 'background':
            data['cover_%s_url' % k] = urlparse(getattr(convert(channel, 'cover', 'CHANNEL'), k)).path

    return add_to_index(data, mappings.CHANNEL_INDEX, mappings.CHANNEL_TYPE, id=channel.id, bulk=bulk, refresh=refresh)


def add_video_to_index(video_instance, bulk=False, refresh=False, no_check=False):
    if not check_es(no_check):
        return

    data = dict(
        id=video_instance.id,
        public=video_instance.video_rel.visible,
        video=dict(
            id=video_instance.video,
            thumbnail_url=video_instance.video_rel.default_thumbnail,
            source=video_instance.video_rel.source,
            source_id=video_instance.video_rel.source_videoid,
            source_username=video_instance.video_rel.source_username,
            date_published=video_instance.video_rel.date_published,
            duration=video_instance.video_rel.duration),
        title=video_instance.video_rel.title,
        channel=video_instance.channel,
        category=video_instance.category,
        date_added=video_instance.date_added,
        position=video_instance.position,
        locales=locale_dict_from_object(video_instance.metas))
    return add_to_index(data, mappings.VIDEO_INDEX, mappings.VIDEO_TYPE, id=video_instance.id, bulk=bulk, refresh=refresh)


def remove_channel_from_index(channel_id):
    if not check_es():
        return

    try:
        es_connection.delete(mappings.CHANNEL_INDEX, mappings.CHANNEL_TYPE, channel_id)
    except pyes.exceptions.NotFoundException:
        app.logger.warning("Failed to remove channel '{}' from index".format(channel_id))


def remove_video_from_index(video_id):
    if not check_es():
        return

    try:
        es_connection.delete(mappings.VIDEO_INDEX, mappings.VIDEO_TYPE, video_id)
    except pyes.exceptions.NotFoundException:
        app.logger.warning("Failed to remove video '{}' from index".format(video_id))
