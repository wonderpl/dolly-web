import logging
from flask import json
import datetime
import pyes
from ast import literal_eval
from urlparse import urlparse
from sqlalchemy.orm import joinedload
from . import mappings
from . import es_connection
from . import use_elasticsearch
from . import exceptions
from rockpack.mainsite import app
from rockpack.mainsite.helpers.db import ImageType
from rockpack.mainsite.core.dbapi import db

logger = logging.getLogger(__name__)


class ESObjectIndexer(object):

    indexes = {
        'channel': {
            'index': mappings.INDEX,
            'type': mappings.CHANNEL_TYPE,
            'mapping': mappings.channel_mapping
        },
        'video': {
            'index': mappings.INDEX,
            'type': mappings.VIDEO_TYPE,
            'mapping': mappings.video_mapping
        },
        'user': {
            'index': mappings.INDEX,
            'type': mappings.USER_TYPE,
            'mapping': mappings.user_mapping
        },
    }

    class InvalidIndexingType(Exception):
        pass

    def __init__(self, _type, bulk=False):
        """ Inserts/Updates a document into elasticsearch

            _type - string - can be of 'channel', 'video', 'user'
            bulk  - bool   - if True, document will be queued up
                                before being flushed to es.
                                A final manual flush needs to be
                                performed at the end """
        if _type not in ('channel', 'video', 'user'):
            raise self.InvalidIndexingType('%s is not a valid index type' % _type)
        self.indexing_type = _type
        self.bulk = bulk

    def insert(self, document_id, data):
        try:
            return es_connection.index(
                data,
                self.indexes[self.indexing_type]['index'],
                self.indexes[self.indexing_type]['type'],
                id=document_id,
                bulk=self.bulk
            )
        except Exception, e:
            app.logger.exception(
                "Failed to insert record to index '%s' with id '%s' with: %s",
                self.indexes[self.indexing_type]['index'],
                document_id,
                str(e))

    def update(self, document_id, data):
        try:
            return es_connection.update(
                self.indexes[self.indexing_type]['index'],
                self.indexes[self.indexing_type]['type'],
                document_id,
                script=data,
                bulk=self.bulk
            )
        except pyes.exceptions.DocumentMissingException, e:
            raise exceptions.DocumentMissingException(e)

    def delete(self, ids):
        if not ids:
            return

        if not isinstance(ids, basestring):
            ids = list(ids)
        else:
            raise TypeError('ids shoulds be a list')

        self.delete_by_query(pyes.IdsQuery(ids))

    def delete_by_query(self, query):
        try:
            es_connection.delete_by_query(
                self.indexes[self.indexing_type]['index'],
                self.indexes[self.indexing_type]['type'],
                query
            )
        except pyes.exceptions.NotFoundException, e:
            raise exceptions.DocumentMissingException(e)

    @staticmethod
    def flush():
        """ Must be called at the end of insert/update operations
            to ensure the entire group of documents are inserted/updated """
        es_connection.flush_bulk(forced=True)

    def refresh(self):
        es_connection.indices.refresh(self.indexes[self.indexing_type]['index'])


class ESInserter(object):
    def __init__(self, index_type, manager):
        self.index_type = index_type
        self.manager = manager

    def insert(self, document_id, document):
        rep = self.manager.insert_mapper(document)
        self.manager.indexer.insert(document_id, rep)
        if app.config.get('FORCE_INDEX_INSERT_REFRESH', False) and not self.manager.indexer.bulk:
            self.manager.indexer.refresh()

    def refresh(self):
        self.manager.indexer.refresh()

    def flush_bulk(self):
        self.manager.indexer.flush()


class ESUpdater(object):
    def __init__(self, index_type, manager):
        self.index_type = index_type
        self.manager = manager
        self.document_id = None
        self.partial_document = []

    def set_document_id(self, id):
        self.document_id = id

    def add_field(self, field, value):
        item = self.manager.update_mapper(field, value)
        self.partial_document.append(item)

    def update(self):
        data = ''.join(self.partial_document)
        self.manager.indexer.update(self.document_id, data)

    def flush_bulk(self):
        self.manager.indexer.flush()


class ESObject(object):

    def __init__(self, bulk=False):
        self.indexer = ESObjectIndexer(self._type, bulk=bulk)

    def update_mapper(self, field, value):

        class DateEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, datetime.datetime):
                    return obj.isoformat()
                return json.JSONEncoder.default(self, obj)

        def construct_update_string(prefix, val):
            if isinstance(val, dict):
                final = ''
                for k, v in val.iteritems():
                    this = prefix + "['%s']" % k
                    final = construct_update_string(this, v) + final
                return final
            else:
                prefix += " = %s;" % json.dumps(val, ensure_ascii=False, cls=DateEncoder)
            return prefix

        return construct_update_string('ctx._source.%s' % field, value)

    @classmethod
    def inserter(cls, bulk=False):
        return ESInserter(cls._type, cls(bulk=bulk))

    @classmethod
    def updater(cls, bulk=False):
        return ESUpdater(cls._type, cls(bulk=bulk))

    @classmethod
    def delete(cls, ids):
        d = ESObjectIndexer(cls._type)
        d.delete(ids)

    @staticmethod
    def flush():
        ESObjectIndexer.flush()


class ESUser(ESObject):

    _type = 'user'

    #TODO: add insert mapper


class ESVideo(ESObject):

    _type = 'video'

    def insert_mapper(self, video):
        mapped = ESVideoAttributeMap(video)
        return dict(
            id=mapped.id,
            public=mapped.public,
            video=mapped.video,
            title=mapped.title,
            channel=mapped.channel,
            channel_title=mapped.channel_title,
            category=mapped.category,
            date_added=mapped.date_added,
            position=mapped.position,
            locales=mapped.locales,
            recent_user_stars=mapped.recent_user_stars(),
            country_restriction=mapped.country_restriction(),
            child_instance_count=mapped.child_instance_count,
            most_influential=mapped.most_influential,
            owner=mapped.owner
        )

    @classmethod
    def delete_channel_videos(cls, channelid):
        query = pyes.TermQuery('channel', channelid)
        ESObjectIndexer(cls._type).delete_by_query(query)


class ESChannel(ESObject):

    _type = 'channel'

    def insert_mapper(self, channel):
        mapped = ESChannelAttributeMap(channel)
        data = dict(
            id=mapped.id,
            public=mapped.public,
            category=mapped.category,
            locales=mapped.locales,
            owner=mapped.owner,
            subscriber_count=mapped.subscriber_count,
            date_added=mapped.date_added,
            date_updated=mapped.date_updated,
            date_published=mapped.date_published,
            description=mapped.description,
            resource_url=mapped.resource_url,
            title=mapped.title,
            ecommerce_url=mapped.ecommerce_url,
            favourite=mapped.favourite,
            verified=mapped.verified,
            update_frequency=mapped.update_frequency,
            subscriber_frequency=mapped.subscriber_frequency,
            editorial_boost=mapped.editorial_boost,
            cover=mapped.cover,
            keywords=mapped.keywords,
            promotion=mapped.promotion,
            normalised_rank=mapped.normalised_rank,
            video_count=mapped.video_count
        )

        if app.config.get('SHOW_OLD_CHANNEL_COVER_URLS', True):
            data['cover_thumbnail_large_url'] = mapped.cover_thumbnail_large_url
            data['cover_thumbnail_small_url'] = mapped.cover_thumbnail_small_url
            data['cover_background_url'] = mapped.cover_background_url

        return data


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


def convert_image_path(obj, attr, type_):
    """ Gets the url of the object from a string
        if path object is unavailable on parent """
    obj_attr = getattr(obj, attr)
    if isinstance(obj_attr, basestring) or obj_attr is None:
        return ImageType(type_).process_result_value(obj_attr, None)
    return obj_attr


class ESVideoAttributeMap:
    def __init__(self, video_instance):
        self.video_instance = video_instance

    def get_country_restrictions(self):
        countries = dict(
            allow=[],
            deny=[])

        for r in self.video_instance.video_rel.restrictions:
            if r.relationship == 'allow':
                countries['allow'].append(r.country)
            else:
                countries['deny'].append(r.country)

        return countries

    def video_stars(self):
        from rockpack.mainsite.services.user.models import UserActivity
        stars = UserActivity.query.filter(
            UserActivity.action == 'star',
            UserActivity.object_type == 'video_instance',
            UserActivity.object_id == self.video_instance.id,
        ).distinct().with_entities(
            UserActivity.user,
            UserActivity.date_actioned
        ).order_by('date_actioned desc')[:10]
        return [_[0] for _ in stars]

    @property
    def id(self):
        return self.video_instance.id

    @property
    def public(self):
        return self.video_instance.video_rel.visible

    @property
    def video(self):
        return dict(
            id=self.video_instance.video,
            thumbnail_url=self.video_instance.video_rel.default_thumbnail,
            source=self.video_instance.video_rel.source,
            source_id=self.video_instance.video_rel.source_videoid,
            source_username=self.video_instance.video_rel.source_username,
            date_published=self.video_instance.video_rel.date_published,
            duration=self.video_instance.video_rel.duration)

    @property
    def title(self):
        return self.video_instance.video_rel.title

    @property
    def channel(self):
        return self.video_instance.channel

    @property
    def channel_title(self):
        return self.video_instance.video_channel.title

    @property
    def category(self):
        return self.video_instance.category

    @property
    def date_added(self):
        return self.video_instance.date_added

    @property
    def position(self):
        return self.video_instance.position

    @property
    def locales(self):
        return locale_dict_from_object(self.video_instance.metas)

    @property
    def child_instance_count(self):
        """ Initialising value only

        Should be computed offline hence forth """
        return 0

    @property
    def owner(self):
        owner = self.video_instance.video_channel.owner_rel
        return dict(
            avatar=urlparse(convert_image_path(owner, 'avatar', 'AVATAR').thumbnail_medium).path,
            display_name=owner.display_name,
            resource_url=urlparse(owner.resource_url).path)

    @property
    def most_influential(self):
        # Default to True so that it automatically
        # shows up in search
        return True

    def recent_user_stars(self, empty=False):
        if empty:
            return []
        return self.video_stars()

    def country_restriction(self, empty=False):
        if empty:
            return dict(
                allow=[],
                deny=[])
        return self.get_country_restrictions()


class ESChannelAttributeMap:
    def __init__(self, channel):
        self.channel = channel

    def generate_cover_url(self, name):
        return urlparse(getattr(convert_image_path(self.channel, 'cover', 'CHANNEL'), name)).path

    @property
    def id(self):
        return self.channel.id

    @property
    def public(self):
        return self.channel.public

    @property
    def category(self):
        return self.channel.child_parent_for_category()

    @property
    def locales(self):
        return locale_dict_from_object(self.channel.metas)

    @property
    def owner(self):
        return self.channel.owner

    @property
    def subscriber_count(self):
        return self.channel.subscriber_count

    @property
    def date_added(self):
        return self.channel.date_added

    @property
    def date_updated(self):
        return self.channel.date_updated

    @property
    def date_published(self):
        return self.channel.date_published

    @property
    def description(self):
        return self.channel.description

    @property
    def resource_url(self):
        return urlparse(self.channel.get_resource_url()).path

    @property
    def title(self):
        return self.channel.title

    @property
    def ecommerce_url(self):
        return self.channel.ecommerce_url

    @property
    def favourite(self):
        return self.channel.favourite

    @property
    def verified(self):
        return self.channel.verified

    @property
    def update_frequency(self):
        return self.channel.update_frequency

    @property
    def subscriber_frequency(self):
        return self.channel.subscriber_frequency

    @property
    def editorial_boost(self):
        return self.channel.editorial_boost

    @property
    def cover(self):
        aoi = None
        # aoi may come in as a string which needs to be eval'd
        # eg. from cms entry
        if self.channel.cover_aoi and isinstance(self.channel.cover_aoi, basestring):
            aoi = literal_eval(self.channel.cover_aoi)

        return dict(
            thumbnail_url=urlparse(convert_image_path(self.channel, 'cover', 'CHANNEL').url).path,
            aoi=aoi
        )

    @property
    def cover_thumbnail_large_url(self):
        return self.generate_cover_url('thumbnail_large')

    @property
    def cover_thumbnail_small_url(self):
        return self.generate_cover_url('thumbnail_small')

    @property
    def cover_background_url(self):
        return self.generate_cover_url('background')

    @property
    def keywords(self):
        return [self.channel.owner_rel.display_name.lower(), self.channel.owner_rel.username.lower()]

    @property
    def promotion(self):
        return self.channel.promotion_map()

    @property
    def normalised_rank(self):
        return {'en-us': 0.0, 'en-gb': 0.0}

    @property
    def video_count(self):
        return len(self.channel.video_instances)


def add_to_index(data, index, _type, id, bulk=False, refresh=False):
    try:
        return es_connection.index(data, index, _type, id=id, bulk=bulk)
    except Exception as e:
        app.logger.exception("Failed to insert record to index '%s' with id '%s' with: %s", index, id, str(e))
    else:
        if refresh or app.config.get('FORCE_INDEX_INSERT_REFRESH', False):
            es_connection.indices.refresh(index)


def add_user_to_index(user, bulk=False, refresh=False, no_check=False):
    if not use_elasticsearch():
        return

    urlpath = lambda u: urlparse(u).path
    if user.brand:
        cover = convert_image_path(user, 'brand_profile_cover', 'BRAND_PROFILE')
    else:
        cover = convert_image_path(user, 'profile_cover', 'PROFILE')
    data = dict(
        id=user.id,
        avatar_thumbnail_url=urlpath(convert_image_path(user, 'avatar', 'AVATAR').url),
        resource_url=urlpath(user.resource_url),
        display_name=user.display_name,
        username=user.username,
        profile_cover_url=urlpath(cover.url),
        description=user.description,
        site_url=user.site_url,
        brand=user.brand,
        subscriber_count=user.subscriber_count,
    )
    return add_to_index(data, mappings.USER_INDEX, mappings.USER_TYPE, id=user.id, bulk=bulk, refresh=refresh)


def update_user_categories(user_ids):
    from rockpack.mainsite.services.video.models import Channel

    query = db.session.query(Channel.category, Channel.owner).filter(
        Channel.public.is_(True),
        Channel.visible.is_(True),
        Channel.deleted.is_(False),
        Channel.owner.in_(user_ids)
    ).order_by(Channel.owner)

    category_map = {}

    for category, owner in query:
        if category is not None:
            category_map.setdefault(owner, []).append(category)

    this_user = ''
    cat_list = []

    for user, category in category_map.iteritems():
        if this_user != user:
            if this_user:
                eu = ESUser.updater(bulk=True)
                eu.set_document_id(this_user)
                eu.add_field('category', list(set(cat_list)))
                eu.update()
            # reset
            this_user = user
            cat_list = []

        cat_list.extend(category)

    es_connection.flush_bulk(forced=True)


def add_channel_to_index(channel, bulk=False, no_check=False):
    if not use_elasticsearch():
        return
    es_channel = ESChannel.inserter(bulk=bulk)
    es_channel.insert(channel.id, channel)

    update_user_categories(user_ids=[channel.owner])


def update_channel_to_index(channel, no_check=False):
    if not use_elasticsearch():
        return

    es_channel = ESChannel.updater()

    mapped = ESChannelAttributeMap(channel)
    data = dict(
        public=mapped.public,
        category=mapped.category,
        locales=mapped.locales,
        owner=mapped.owner,
        subscriber_count=mapped.subscriber_count,
        date_added=mapped.date_added,
        date_updated=mapped.date_updated,
        date_published=mapped.date_published,
        description=mapped.description,
        resource_url=mapped.resource_url,
        title=mapped.title,
        ecommerce_url=mapped.ecommerce_url,
        favourite=mapped.favourite,
        verified=mapped.verified,
        update_frequency=mapped.update_frequency,
        subscriber_frequency=mapped.subscriber_frequency,
        editorial_boost=mapped.editorial_boost,
        cover=mapped.cover,
        keywords=mapped.keywords,
        promotion=mapped.promotion,
    )

    es_channel.set_document_id(channel.id)
    for field, value in data.iteritems():
        es_channel.add_field(field, value)
    try:
        return es_channel.update()
    except exceptions.DocumentMissingException, e:
        # If the channel doesn't exist we need to create it
        # (likely it was private and now public).
        # Switch to an insert statement instead.
            try:
                add_channel_to_index(channel)
            except Exception, e:
                app.logger.error('Failed to insert channel after failed update with: %s', str(e))

    update_user_categories([channel.owner])


def add_video_to_index(video_instance, bulk=False, no_check=False):
    if not use_elasticsearch():
        return

    es_video = ESVideo.inserter()
    es_video.insert(video_instance.id, video_instance)


def es_update_channel_videos(extant=[], deleted=[], async=app.config.get('ASYNC_ES_VIDEO_UPDATES', False)):
    """ Updates the es documents for videos belonging to channels
        extant - list of strings
        deleted - list of strings
        async - boolean """

    if not use_elasticsearch() or (not extant and not deleted):
        return

    if async:
        from rockpack.mainsite.video_update_sqs_processor import _write_message
        return _write_message(dict(extant=extant, deleted=deleted))

    from rockpack.mainsite.services.video import models
    from . import update

    channel_ids = []
    video_ids = []

    # XXX: This is a nasty hack to allow the VideoInstance query to proceed
    # when this is called from sqlalchemy's after_commit signal
    if models.VideoInstance.query.session.transaction._state.name == 'COMMITTED':
        models.VideoInstance.query.session.transaction._state = None

    if extant:
        all_instances = models.VideoInstance.query.filter(
            models.VideoInstance.id.in_(extant)
        ).options(
            joinedload(models.VideoInstance.video_channel)
        )
    else:
        all_instances = []

    # Run through the instance data and get
    # the channel and video ids from the
    # instances that are to be added/deleted
    es_video = ESVideo.inserter(bulk=True)
    for instance in all_instances:
        channel_ids.append(instance.channel)
        video_ids.append(instance.video)
        # Insert any instances to es as necessary
        # while we're looping through everything
        if instance.id in extant:
            es_video.insert(instance.id, instance)
    es_video.flush_bulk()

    if deleted:
        ESVideo.delete(deleted)

    update._update_most_influential_video(video_ids)
    update._update_video_related_channel_meta(channel_ids)


def remove_channel_from_index(channel_id):
    if not use_elasticsearch():
        return

    try:
        ESChannel.delete([channel_id])
    except exceptions.DocumentMissingException:
        pass
    else:
        ESVideo.delete_channel_videos(channel_id)

    from rockpack.mainsite.services.video.models import Channel
    user_id = db.session.query(Channel.owner).filter(Channel.id == channel_id).first()
    if user_id:
        update_user_categories([user_id[0]])


def remove_video_from_index(video_id):
    if not use_elasticsearch():
        return

    try:
        ESVideo.delete([video_id])
    except exceptions.DocumentMissingException:
        pass
