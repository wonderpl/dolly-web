import sys
import time
import decimal
import logging
from datetime import datetime, timedelta
from functools import wraps
from itertools import groupby
from flask import json
import pyes
from sqlalchemy import distinct, func, literal
from sqlalchemy.orm import aliased, joinedload
from . import api
from . import exceptions
from rockpack.mainsite import app
from rockpack.mainsite.core.dbapi import readonly_session
from rockpack.mainsite.core.es import FlushTimer
from rockpack.mainsite.core.es import es_connection
from rockpack.mainsite.core.es import migration
from rockpack.mainsite.core.es.api import (
    ESObjectIndexer, ESVideo, ESChannel, ESSearchSuggestion,
    ESVideoAttributeMap, update_user_categories, update_user_subscription_count)


def main_category(cat_count_map):
    """Return the category that has more than 60% of the count."""
    threshold = sum(cat_count_map.values()) * 0.6
    return next((cat for cat, count in cat_count_map.iteritems() if count >= threshold), None)


def start_flush_timer(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        FlushTimer().start()
        return func(*args, **kwargs)
    return decorator


class Indexing(object):

    def __init__(self, doc_type):
        self.conn = es_connection
        self.indexer = ESObjectIndexer(doc_type)
        self.doc_type = doc_type

    @classmethod
    def delete_indices_for(cls, alias):
        for index in migration.Aliasing.get_base_indices_for(alias):
            migration.Aliasing.delete_index(index)

    def create_index(self, rebuild=False):
        if not self.doc_type.strip():
            return

        aliasing = migration.Aliasing(self.doc_type)
        try:
            current_index = aliasing.current_index()
            app.logger.info('index for %s already exists', self.doc_type)
        except:
            app.logger.info('creating new index for %s', self.doc_type)
            index_name = aliasing.create_new_index()
            aliasing.assign(aliasing.alias, index_name)
        else:
            if rebuild:
                app.logger.info('rebuilding index for %s', self.doc_type)
                aliasing.delete_index(current_index)
                index_name = aliasing.create_new_index()
                aliasing.assign(aliasing.alias, index_name)

    def create_mapping(self):
        self.conn.indices.put_mapping(
            self.indexer.doc_type,
            self.indexer.mapping,
            [self.indexer.index])
        self.conn.indices.refresh(self.indexer.index)

    @classmethod
    def create_all_indexes(cls, rebuild=False):
        for doc_type in ESObjectIndexer.indexes.keys():
            cls(doc_type).create_index(rebuild)

    @classmethod
    def create_all_mappings(cls):
        for doc_type in ESObjectIndexer.indexes.keys():
            cls(doc_type).create_mapping()


class ESAliasing:

    @staticmethod
    def index_prefix_for_doc_type(doc_type):
        index = ESObjectIndexer.indexes[doc_type]['index']
        # Sanity check
        real_doc_type = ESObjectIndexer.indexes[doc_type]['type']
        return index + '_' + real_doc_type

    @staticmethod
    def build_new_index_name(doc_type):
        """ Builds a name from the current time in seconds since epoch,
            the name_part and site name.
            E.g. if name_part = 'channel'
                    index_name = rockpack_channel_1385124160 """
        index_prefix = ESAliasing.index_prefix_for_doc_type(doc_type)
        timestamp = datetime.utcnow().strftime("%s")
        return '%s_%s' % (index_prefix, timestamp)

    @staticmethod
    def get_mapping_for_alias(alias):
        return ESObjectIndexer.indexes[alias]['mapping']

    @classmethod
    def new_index_for_type(cls, doc_type, mapping):
        index_name = cls.build_new_index_name(doc_type)
        es_connection.create_index(index_name)
        es_connection.put_mapping(doc_type=doc_type, mapping=mapping, indices=[index_name])
        return index_name


class ESMigration(object):

    @staticmethod
    def migrate_alias(doc_type):
        """ Creates a new index with the mapping specified
            in the mappings file and reassigns the current
            alias to the new index """

        def prompt(msg):
            val = raw_input(msg)
            if val in 'Nn':
                sys.exit(1)
            if val in 'Yy':
                return True
            return False

        aliasing = migration.Aliasing(doc_type)

        new_index = ''
        try:
            old_index = aliasing.current_index()
            new_index = aliasing.create_new_index()
            aliasing.reindex_to(new_index)
            aliasing.integrity_check(old_index, new_index, aliasing.doc_type)
            aliasing.reassign_to(new_index)
            # Final reindex to catch any missed imports
            # But lets give it some time to settle first
            time.sleep(2)
            aliasing.reindex_to(new_index, with_version=True)
        except Exception, e:
            app.logger.error('Alias swap failed. Rolling back migration because %s from %s', str(e), type(e))
            if new_index.strip():
                app.logger.error('Deleting new index %s (existing index %s unaffected)', new_index, old_index)
                aliasing.delete_index(new_index)
            return
        else:
            while(1):
                if prompt("Delete old index? "):
                    if prompt("You sure you want to do that? "):
                        aliasing.delete_index(old_index)
                        break


@start_flush_timer
def full_user_import(start=None, stop=None):
    from rockpack.mainsite.services.user import models

    with app.test_request_context():
        users_to_delete = models.User.query.filter(models.User.is_active == False)
        if start:
            users_to_delete = users_to_delete.filter(models.User.date_updated.between(start, stop))

        delete = [u[0] for u in users_to_delete.values('id')]

        if delete:
            api.ESUser.delete(delete)
            api.ESUser.flush()

    imp = DBImport()
    imp.import_users(start=start, stop=stop, automatic_flush=False)
    update_user_categories(automatic_flush=False, start=start, stop=stop)
    update_user_subscription_count(start=start, stop=stop, automatic_flush=False)

    api.ESUser.flush()


@start_flush_timer
def full_channel_import(start=None, stop=None):
    from rockpack.mainsite.services.video import models

    with app.test_request_context():
        channels_to_delete = models.Channel.query.filter(
            (models.Channel.public == False) |
            (models.Channel.deleted == True) |
            (models.Channel.visible == False)
        )

        if start:
            channels_to_delete = channels_to_delete.filter(models.Channel.date_updated.between(start, stop))

        delete = [c[0] for c in channels_to_delete.values('id')]

        if delete:
            api.ESChannel.delete(delete)
            api.ESChannel.flush()

    imp = DBImport()
    imp.import_channels(start=start, stop=stop, automatic_flush=False)
    imp.import_average_category(start=start, stop=stop, automatic_flush=False)
    imp.import_video_channel_terms(start=start, stop=stop, automatic_flush=False)

    api.ESChannel.flush()


@start_flush_timer
def full_video_import(start=None, stop=None, prefix=None):
    from rockpack.mainsite.services.video import models

    with app.test_request_context():
        videos_to_delete = models.VideoInstance.query.join(
            models.Video,
            models.VideoInstance.video == models.Video.id
        ).filter(
            (models.VideoInstance.deleted == True) |
            (models.Video.visible == False))

        if start:
            videos_to_delete = videos_to_delete.filter(
                (models.VideoInstance.date_updated.between(start, stop)) |
                (models.Video.date_updated.between(start, stop)))

        if prefix:
            videos_to_delete = videos_to_delete.filter(
                models.VideoInstance.id.like(prefix.replace('_', '\\_') + '%'))

        delete = [v[0] for v in videos_to_delete.values(models.VideoInstance.id)]

        if delete:
            api.ESVideo.delete(delete)
            api.ESVideo.flush()

    imp = DBImport()
    imp.import_videos(prefix=prefix, start=start, stop=stop, automatic_flush=False)
    imp.import_dolly_video_owners(prefix=prefix, start=start, stop=stop, automatic_flush=False)
    imp.import_video_stars(prefix=prefix, automatic_flush=False, start=start, stop=stop)
    imp.import_comment_counts(prefix=prefix, automatic_flush=False, start=start, stop=stop)

    api.ESVideo.flush()


class DBImport(object):

    def __init__(self):
        self.conn = es_connection
        self.indexing = ESObjectIndexer.indexes

    def print_percent_complete(self, current, total):
        n = round(current / float(total) * 100, 1)
        if n < 1:
            n = 1
        if n % 1 == 0.0 or n == 1:
            print int(n), "percent complete                                                \r",
            sys.stdout.flush()

    def import_users(self, start=None, stop=None, automatic_flush=True):
        from rockpack.mainsite.services.user import models

        with app.test_request_context():
            users = models.User.query.filter(models.User.is_active == True)

            if start:
                users = users.filter(models.User.date_updated.between(start, stop))

            total = users.count()

            app.logger.debug('importing {} users'.format(total))

            start = time.time()
            count = 1
            for users in users.yield_per(6000):
                api.add_user_to_index(users, bulk=True, no_check=True)
                if app.logger.isEnabledFor(logging.DEBUG):
                    self.print_percent_complete(count, total)
                count += 1

            if automatic_flush:
                self.conn.flush_bulk(forced=True)

            app.logger.debug('finished in {}'.format(time.time() - start, 'seconds'))

    def import_channels(self, start=None, stop=None, automatic_flush=True):
        from rockpack.mainsite.services.video.models import Channel, VideoInstance, Video

        with app.test_request_context():
            channels = Channel.query.filter(
                Channel.public == True,
                Channel.visible == True,
                Channel.deleted == False
            ).options(
                joinedload(Channel.category_rel),
                joinedload(Channel.metas),
                joinedload(Channel.owner_rel)
            )

            if start:
                channels = channels.filter(Channel.date_updated.between(start, stop))

            app.logger.debug('importing {} PUBLIC channels\r'.format(channels.count()))

            func_start = time.time()
            ec = ESChannel.inserter(bulk=True)
            count = 1
            total = channels.count()

            query = VideoInstance.query.join(
                Video,
                (Video.id == VideoInstance.video) &
                (Video.visible == True)
            ).filter(VideoInstance.deleted == False).group_by(VideoInstance.channel)

            if start:
                # Restrict the counts selected to the channels we want
                query = query.join(
                    Channel,
                    (Channel.id == VideoInstance.channel) &
                    (Channel.date_updated.between(start, stop))
                )

            query = query.values(VideoInstance.channel, func.count(VideoInstance.id))

            video_counts = dict(query)

            for channel in channels.yield_per(6000):
                channel._video_count = video_counts.get(channel.id) or 0
                ec.insert(channel.id, channel)
                if app.logger.isEnabledFor(logging.DEBUG):
                    self.print_percent_complete(count, total)
                count += 1

            if automatic_flush:
                ec.flush_bulk()

            app.logger.debug('finished in {} seconds'.format(time.time() - func_start))

    def import_search_suggestions(self):
        from rockpack.mainsite.services.video.models import Video

        with app.test_request_context():
            inserter = ESSearchSuggestion.inserter(bulk=True)
            videos = Video.query.filter_by(visible=True).with_entities(
                Video.id,
                literal('video').label('type'),
                Video.title.label('query'),
                Video.star_count.label('weight'),
            )
            for video in videos.yield_per(6000):
                inserter.insert(video.id, video)

            inserter.flush_bulk()

    def import_videos(self, prefix=None, start=None, stop=None, recent_user_stars=False, automatic_flush=True):
        from rockpack.mainsite.services.video.models import (Channel, Video, VideoInstanceLocaleMeta,
                                                             VideoInstance)
        from rockpack.mainsite.services.user.models import User

        with app.test_request_context():
            query = VideoInstance.query.join(
                Channel,
                Channel.id == VideoInstance.channel
            ).join(Video).outerjoin(
                VideoInstanceLocaleMeta,
                VideoInstance.id == VideoInstanceLocaleMeta.video_instance
            ).outerjoin(
                User,
                (User.id == VideoInstance.original_channel_owner) &
                (User.is_active == True)
            ).options(
                joinedload(VideoInstance.metas)
            ).options(
                joinedload(VideoInstance.video_rel)
            ).options(
                joinedload(VideoInstance.video_channel)
            ).options(
                joinedload(VideoInstance.original_channel_owner_rel)
            ).filter(
                VideoInstance.deleted == False,
                Video.visible == True
            )

            if prefix:
                query = query.filter(VideoInstance.id.like(prefix.replace('_', '\\_') + '%'))

            if start:
                query = query.filter(VideoInstance.date_updated.between(start, stop))

            total = query.count()
            app.logger.debug('importing {} videos'.format(total))
            start_timer = time.time()
            done = 1

            ev = ESVideo.inserter(bulk=True)
            channel_ids = []
            for v in query.yield_per(6000):
                mapped = ESVideoAttributeMap(v)
                rep = dict(
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
                    recent_user_stars=mapped.recent_user_stars(empty=not recent_user_stars),
                    country_restriction=mapped.country_restriction(empty=True),
                    comments=mapped.comments(empty=True),
                    child_instance_count=mapped.child_instance_count,
                    link_url=mapped.link_url,
                    link_title=mapped.link_title,
                    tags=mapped.tags,
                    is_favourite=mapped.is_favourite,
                    most_influential=mapped.most_influential,
                    original_channel_owner=mapped.original_channel_owner,
                    label=mapped.label,
                )
                ev.manager.indexer.insert(v.id, rep)

                if app.logger.isEnabledFor(logging.DEBUG):
                    self.print_percent_complete(done, total)
                done += 1

                if start and v.channel not in channel_ids:
                    channel_ids.append(v.channel)

            if start:
                # We'll want to update channel counts that
                # may not get trigger elsewhere
                self.import_channel_video_counts(channel_ids)

            if automatic_flush:
                ev.flush_bulk()

            app.logger.debug('finished in {} seconds'.format(time.time() - start_timer))

    def import_channel_video_counts(self, channel_ids):
        if channel_ids:

            from rockpack.mainsite.services.video.models import Channel, VideoInstance

            with app.test_request_context():
                query = Channel.query.join(
                    VideoInstance,
                    (VideoInstance.channel == Channel.id) &
                    (VideoInstance.deleted == False)
                ).filter(
                    Channel.id.in_(channel_ids)
                ).group_by(
                    Channel.id
                ).values(Channel.id, func.count(Channel.id))

                for channel_id, count in query:
                    try:
                        self.conn.partial_update(
                            self.indexing['channel']['index'],
                            self.indexing['channel']['type'],
                            channel_id,
                            "ctx._source.video_counts = %s" % count
                        )
                    except pyes.exceptions.ElasticSearchException:
                        pass

    def import_dolly_video_owners(self, prefix=None, start=None, stop=None, automatic_flush=True):
        """ Import all the owner attributes of
            a video instance belonging to a channel """

        from rockpack.mainsite.services.video.models import Channel, VideoInstance
        from rockpack.mainsite.services.user.models import User

        with app.test_request_context():
            instances = VideoInstance.query.join(
                Channel,
                (VideoInstance.channel == Channel.id) &
                (Channel.public == True) &
                (Channel.visible == True) &
                (Channel.deleted == False)
            ).join(
                User,
                User.id == Channel.owner
            ).filter(
                VideoInstance.deleted == False
            )

            if prefix:
                instances = instances.filter(VideoInstance.id.like(prefix.replace('_', '\\_') + '%'))

            if start:
                instances = instances.filter(VideoInstance.date_updated.between(start, stop))

            instances = instances.with_entities(VideoInstance, User).order_by(VideoInstance.channel)

            total = instances.count()
            done = 1

            current_user_dict = None
            current_channel = None

            ec = ESVideo.updater(bulk=True)
            for instance, user in instances.yield_per(6000):
                if instance.channel != current_channel:
                    # Duck punch the user on for perf
                    instance.owner_rel = user
                    mapped = ESVideoAttributeMap(instance)
                    current_user_dict = mapped.owner
                    current_channel = instance.channel

                ec.set_document_id(instance.id)
                ec.add_field('owner', current_user_dict)
                ec.update()
                ec.reset()

                if app.logger.isEnabledFor(logging.DEBUG):
                    self.print_percent_complete(done, total)
                done += 1

            if automatic_flush:
                self.conn.flush_bulk(forced=True)

    def import_user_categories(self):
        update_user_categories()

    def import_comment_counts(self, prefix=None, automatic_flush=True, start=None, stop=None):
        from rockpack.mainsite.services.video.models import VideoInstanceComment, VideoInstance, Video
        from rockpack.mainsite.core.dbapi import db

        counts = db.session.query(VideoInstance.id, func.count(VideoInstance.id)).join(
            VideoInstanceComment,
            VideoInstanceComment.video_instance == VideoInstance.id
        ).join(
            Video,
            (Video.id == VideoInstance.video) &
            (Video.visible == True)
        ).filter(VideoInstance.deleted == False)

        if prefix:
            counts = counts.filter(VideoInstance.id.like(prefix.replace('_', '\\_') + '%'))

        if start:
            counts = counts.filter(VideoInstanceComment.date_added.between(start, stop))

        counts = counts.group_by(
            VideoInstance.id
        )

        app.logger.debug('%d video%s with comments' % (counts.count(), 's' if counts.count() > 1 else ''))
        app.logger.debug('Processing ...')

        ev = ESVideo.updater(bulk=True)
        for videoid, count in counts:
            ev.set_document_id(videoid)
            ev.add_field('comments.count', count)
            ev.update()
            ev.reset()

        if automatic_flush:
            ESVideo.flush()

    def import_dolly_repin_counts(self, prefix=None, start=None, stop=None, automatic_flush=True):
        from rockpack.mainsite.services.video.models import VideoInstance, Video

        with app.test_request_context():
            child = aliased(VideoInstance, name='child')
            query = readonly_session.query(
                VideoInstance.id,
                VideoInstance.video,
                child.source_channel,
                func.count(VideoInstance.id)
            ).outerjoin(
                child,
                (VideoInstance.video == child.video) &
                (VideoInstance.channel == child.source_channel)
            ).join(
                Video,
                (Video.id == VideoInstance.video) &
                (Video.visible == True) &
                (VideoInstance.deleted == False))

            if prefix:
                query = query.filter(VideoInstance.id.like(prefix.replace('_', '\\_') + '%'))

            if start:
                video_ids = VideoInstance.query.filter(
                    VideoInstance.date_updated.between(start, stop)
                ).with_entities(VideoInstance.video).subquery()

                query = query.filter(Video.id.in_(video_ids))

            query = query.group_by(VideoInstance.id, VideoInstance.video, child.source_channel)

            instance_counts = {}
            influential_index = {}

            total = query.count()
            done = 1

            for _id, video, source_channel, count in query.yield_per(6000):
                # Set the count for the video instance
                instance_counts[(_id, video)] = count
                # If the count is higher for the same video that
                # the previous instance, mark this instance as the
                # influential one for this video
                i_id, i_count = influential_index.get(video, [None, 0])

                # Count will always be at least 1
                # but should really be zero if no children
                if not source_channel and count == 1:
                    count = 0
                if (count > i_count) or\
                        (count == i_count) and not source_channel:
                    influential_index.update({video: (_id, count,)})

                if app.logger.isEnabledFor(logging.DEBUG):
                    self.print_percent_complete(done, total)
                done += 1

            total = len(instance_counts)
            done = 1

            ec = ESVideo.updater(bulk=True)
            for (_id, video), count in instance_counts.iteritems():
                ec.set_document_id(_id)
                ec.add_field('child_instance_count', count)
                ec.add_field('most_influential', True if influential_index.get(video, '')[0] == _id else False)
                ec.update()
                ec.reset()

                if app.logger.isEnabledFor(logging.DEBUG):
                    self.print_percent_complete(done, total)
                done += 1

            if automatic_flush:
                ESVideo.flush()

    def import_video_stars(self, prefix=None, automatic_flush=True, start=None, stop=None):
        from rockpack.mainsite.services.user.models import UserActivity

        updated_activity = aliased(UserActivity, name='updated_activity')

        with app.test_request_context():
            query = UserActivity.query.filter(
                UserActivity.action == 'star',
                UserActivity.object_type == 'video_instance'
            ).order_by(
                UserActivity.object_id, UserActivity.date_actioned.desc()
            )

            if start:
                query = query.join(
                    updated_activity,
                    (updated_activity.object_id == UserActivity.object_id) &
                    (updated_activity.date_actioned.between(start, stop)))

            if prefix:
                query = query.filter(UserActivity.object_id.like(prefix.replace('_', '\\_') + '%'))

            ec = ESVideo.updater(bulk=True)
            for instance_id, group in groupby(query.yield_per(200).values(UserActivity.object_id, UserActivity.user), lambda x: x[0]):
                try:
                    ec.set_document_id(instance_id)
                    ec.add_field(
                        'recent_user_stars',
                        list(set([u.encode('utf8') for v, u in group]))[:5]
                    )
                    ec.update()
                except pyes.exceptions.ElasticSearchException:
                    pass
                finally:
                    ec.reset()

            if automatic_flush:
                self.conn.flush_bulk(forced=True)

    def import_video_restrictions(self, automatic_flush=True):
        from rockpack.mainsite.services.video.models import VideoRestriction, VideoInstance, Video, Channel

        with app.test_request_context():
            query = VideoRestriction.query.join(
                VideoInstance,
                VideoInstance.video == VideoRestriction.video
            ).join(Channel, VideoInstance.channel == Channel.id).join(Video, Video.id == VideoRestriction.video).filter(Video.visible == True, Channel.public == True).order_by(VideoInstance.id)

            for relationship in ('allow', 'deny',):
                for instance_id, group in groupby(query.filter(VideoRestriction.relationship == relationship).yield_per(6000).values(VideoInstance.id, VideoRestriction.country), lambda x: x[0]):
                    countries = [c.encode('utf8') for i, c in group]

                    try:
                        self.conn.partial_update(
                            self.indexing['video']['index'],
                            self.indexing['video']['type'],
                            instance_id,
                            "ctx._source.country_restriction.%s = %s" % (relationship, str(countries),)
                        )
                    except pyes.exceptions.ElasticSearchException:
                        pass

                sys.stdout.flush()

                if automatic_flush:
                    self.conn.flush_bulk(forced=True)

    def _partial_update(self, index, id, script, params=None):
        self.conn.update(
            self.indexing[index]['index'],
            self.indexing[index]['type'],
            id,
            script=script,
            bulk=True
        )

    def import_average_category(self, channel_ids=None, start=None, stop=None, automatic_flush=True):
        from rockpack.mainsite.services.video.models import VideoInstance, Channel

        query = readonly_session.query(VideoInstance.category, Channel.id).join(Channel, Channel.id == VideoInstance.channel).order_by(Channel.id)

        if channel_ids:
            query = query.filter(Channel.id.in_(channel_ids))

        if start:
            query = query.filter(Channel.date_updated.between(start, stop))

        category_map = {}
        for instance_cat, channel_id in query:
            channel_cat_counts = category_map.setdefault(channel_id, {})
            current_count = channel_cat_counts.setdefault(instance_cat, 0)
            channel_cat_counts[instance_cat] = current_count + 1

        ec = ESChannel.updater(bulk=True)
        for channel_id, c_map in category_map.iteritems():
            ec.set_document_id(channel_id)
            ec.add_field('category', main_category(c_map))
            ec.update()
            ec.reset()

        if automatic_flush:
            self.conn.flush_bulk(forced=True)

    def import_video_channel_terms(self, prefix=None, start=None, stop=None, automatic_flush=True):
        from rockpack.mainsite.services.video.models import VideoInstance, Channel, Video

        child = aliased(VideoInstance, name='child')

        query = VideoInstance.query.join(
            Channel,
            Channel.id == VideoInstance.channel
        ).join(
            Video,
            Video.id == VideoInstance.video
        ).filter(Channel.public == True, Channel.deleted == False)

        if start:
            query = query.join(child, child.channel == Channel.id).filter(child.date_updated.between(start, stop))

        channel_terms = {}

        total = 0
        start = time.time()

        app.logger.debug('Building data ...')
        for v in query.yield_per(600):
            channel_terms.setdefault(v.channel, []).append(v.video_rel.title)

        app.logger.debug('Updating records in es ...')
        for c_id, terms_list in channel_terms.iteritems():
            try:
                self._partial_update(
                    'channel',
                    c_id,
                    'ctx._source.video_terms = %s' % json.dumps(terms_list)
                )
                self._partial_update(
                    'channel',
                    c_id,
                    'ctx._source.video_count = %s' % len(terms_list)
                )
            except pyes.exceptions.ElasticSearchException, e:
                app.logger.error('Failed to import channel terms with %s', str(e))
            total += 1

        if automatic_flush:
            self.conn.flush_bulk(forced=True)
        app.logger.debug('%s finished in %s seconds', total, time.time() - start)

    def import_channel_share(self, automatic_flush=True):
        from rockpack.mainsite.services.share.models import ShareLink
        from rockpack.mainsite.services.user.models import UserActivity, User
        from rockpack.mainsite.services.video.models import VideoInstance, Channel

        total = 0
        missing = 0
        start = time.time()

        def _normalised(val, max_val, min_val):
            try:
                return (val - min_val) / (abs(max_val) - abs(min_val))
            except (ZeroDivisionError, decimal.DivisionByZero, decimal.InvalidOperation):
                return 0

        def _update_channel_id(id, val, max_val, min_val):
            channel_dict[id] = channel_dict.setdefault(id, 0) + _normalised(val, max_val, min_val)

        # The strength of actions decay until any older than zulu have no effect
        zulu = datetime.now() - timedelta(days=app.config.get('CHANNEL_RANK_ZULU', 1))
        time_since_zulu = (datetime.utcnow() - zulu).total_seconds()

        for locale in ['en-gb', 'en-us']:
            app.logger.debug('starting for %s', locale)
            channel_dict = {}
            channel_shares = {}

            summation = func.sum(
                (time_since_zulu - (func.extract('epoch', datetime.utcnow()) - func.extract('epoch', UserActivity.date_actioned))) / time_since_zulu
            )

            # activity for channels from videos
            query = readonly_session.query(
                distinct(Channel.id).label('channel_id'),
                summation.label('summed')
            ).join(
                VideoInstance, VideoInstance.channel == Channel.id
            ).join(
                UserActivity, UserActivity.object_id == VideoInstance.id
            ).join(
                User, User.id == UserActivity.user
            ).filter(
                UserActivity.action == 'star',
                UserActivity.object_type == 'video_instance',
                UserActivity.date_actioned > zulu,
                User.locale == locale
            ).group_by(Channel.id)

            summed = query.subquery().columns.summed
            q_max, q_min = UserActivity.query.session.query(func.max(summed), func.min(summed)).one()

            for id, count in query.yield_per(6000):
                channel_dict.setdefault(id, {})
                channel_dict[id]['user_activity'] = [count, _normalised(count, q_max, q_min)]
                channel_dict[id]['norm_user_activity'] = _normalised(count, q_max, q_min)

            app.logger.debug('user activity done')

            summation = func.sum(
                (time_since_zulu - (func.extract('epoch', datetime.utcnow()) - func.extract('epoch', ShareLink.date_created))) / time_since_zulu
            )

            # activity for channel shares
            query = readonly_session.query(
                distinct(Channel.id).label('channel_id'),
                summation.label('summed')
            ).join(
                ShareLink,
                ShareLink.object_id == Channel.id
            ).join(
                User, User.id == ShareLink.user
            ).filter(
                Channel.deleted == False,
                Channel.public == True,
                ShareLink.object_type == 'channel',
                ShareLink.date_created > zulu,
                ShareLink.click_count > 0,
                User.locale == locale
            ).group_by(Channel.id)

            summed = query.subquery().columns.summed

            q_max, q_min = ShareLink.query.session.query(func.max(summed), func.min(summed)).one()
            channel_share_vals = (q_max, q_min)

            for id, count in query.yield_per(6000):
                channel_dict.setdefault(id, {})
                channel_shares[id] = count
                channel_dict[id]['share_link_channel'] = [count, _normalised(count, q_max, q_min)]

            app.logger.debug('channel shares done')
            # activity for videos shares of channels
            query = readonly_session.query(
                distinct(Channel.id).label('channel_id'),
                summation.label('summed')
            ).join(
                VideoInstance,
                VideoInstance.channel == Channel.id
            ).join(
                ShareLink,
                ShareLink.object_id == VideoInstance.id
            ).join(
                User, User.id == ShareLink.user
            ).filter(
                Channel.deleted == False,
                Channel.public == True,
                ShareLink.object_type == 'video_instance',
                ShareLink.date_created > zulu,
                ShareLink.click_count > 0,
                User.locale == locale
            ).group_by(Channel.id)

            summed = query.subquery().columns.summed

            q_max, q_min = ShareLink.query.session.query(func.max(summed), func.min(summed)).one()

            for id, count in query.yield_per(6000):
                channel_dict.setdefault(id, {})
                channel_dict[id]['share_link_video'] = [count, _normalised(count, q_max, q_min)]
                val = channel_shares.get(id, 0)
                # We may get None returned in the data
                if None in channel_share_vals:
                    channel_share_vals = [0, 0]
                channel_dict[id]['norm_share_link_channel'] = channel_dict[id].setdefault('norm_share_link_channel', 0) + _normalised(count + val, q_max + channel_share_vals[0], q_min + channel_share_vals[1])

            app.logger.debug('video shares done')

            app.logger.debug('... updating elasticsearch for %s ...', locale)

            done = 1
            i_total = len(channel_dict)
            ec = ESChannel.updater(bulk=True)
            for id, _dict in channel_dict.iteritems():
                try:
                    count = 0
                    for k, v in _dict.iteritems():
                        if k.startswith('norm'):
                            count += v

                    if count == 0:
                        continue

                    ec.set_document_id(id)
                    ec.add_field('normalised_rank[\'%s\']' % locale, float(count))
                    ec.update()

                except exceptions.DocumentMissingException:
                    missing += 1
                finally:
                    ec.reset()
                total += 1
                if app.logger.isEnabledFor(logging.DEBUG):
                    self.print_percent_complete(done, i_total)
                done += 1

            if automatic_flush:
                ESChannel.flush()

        app.logger.debug('%s total updates in two passes. finished in %s seconds (%s channels not in es)', total, time.time() - start, missing)
