import sys
import time
from datetime import datetime, timedelta
from itertools import groupby
from flask import json
from pyes.exceptions import ElasticSearchException
from sqlalchemy import distinct, func
from sqlalchemy.orm import aliased
from sqlalchemy.orm import joinedload
from . import api
from . import exceptions
from rockpack.mainsite import app
from rockpack.mainsite.core.dbapi import readonly_session
from rockpack.mainsite.core.es import es_connection
from rockpack.mainsite.core.es.api import ESObjectIndexer, ESVideo, ESChannel, ESVideoAttributeMap


class Indexing(object):

    def __init__(self):
        self.conn = es_connection

        self.indexes = ESObjectIndexer.indexes

    def delete_index(self, index):
        app.logger.debug('deleting %s index %s', index, self.indexes[index]['index'])
        self.conn.indices.delete_index_if_exists(self.indexes[index]['index'])

    def create_index(self, index, rebuild=False):
        if rebuild:
            self.delete_index(index)
        app.logger.debug('creating %s index %s', index, self.indexes[index]['index'])
        self.conn.indices.create_index(self.indexes[index]['index'])

    def create_all_indexes(self, rebuild=False):
        for index in self.indexes.keys():
            self.create_index(index, rebuild)

    def create_mapping(self, index):
        self.conn.indices.put_mapping(
            self.indexes[index]['type'],
            self.indexes[index]['mapping'],
            [self.indexes[index]['index']])
        self.conn.indices.refresh(self.indexes[index]['index'])

    def create_all_mappings(self):
        for index in self.indexes.keys():
            self.create_mapping(index)


class DBImport(object):

    def __init__(self):
        self.conn = es_connection
        self.indexing = Indexing()

    def print_percent_complete(self, current, total):
        n = round(current / float(total) * 100, 1)
        if n < 1:
            n = 1
        if n % 1 == 0.0 or n == 1:
            print int(n), "percent complete                                                \r",
            sys.stdout.flush()

    def import_users(self):
        from rockpack.mainsite.services.user import models

        with app.test_request_context():
            users = models.User.query
            total = users.count()
            print 'importing {} users'.format(total)
            start = time.time()
            count = 1
            for users in users.yield_per(6000):
                api.add_user_to_index(users, bulk=True, no_check=True)
                self.print_percent_complete(count, total)
                count += 1
            self.conn.flush_bulk(forced=True)
            print 'finished in', time.time() - start, 'seconds'

    def import_channels(self):
        from rockpack.mainsite.services.video.models import Channel

        with app.test_request_context():
            channels = Channel.query.filter(
                Channel.public == True,
                Channel.deleted == False).options(
                    joinedload(Channel.category_rel),
                    joinedload(Channel.metas),
                    joinedload(Channel.owner_rel),
                    joinedload(Channel.video_instances)
                )
            print 'importing {} PUBLIC channels\r'.format(channels.count())
            start = time.time()
            ec = ESChannel.inserter(bulk=True)
            count = 1
            total = channels.count()
            for channel in channels.yield_per(6000):
                ec.insert(channel.id, channel)
                self.print_percent_complete(count, total)
                count += 1
            ec.flush_bulk()
            print 'finished in', time.time() - start, 'seconds'

    def import_videos(self):
        from rockpack.mainsite.services.video.models import Channel, Video, VideoInstanceLocaleMeta, VideoInstance

        with app.test_request_context():
            query = VideoInstance.query.join(
                Channel,
                Channel.id == VideoInstance.channel
            ).join(Video).outerjoin(
                VideoInstanceLocaleMeta,
                VideoInstance.id == VideoInstanceLocaleMeta.video_instance
            ).options(
                joinedload(VideoInstance.metas)
            ).options(
                joinedload(VideoInstance.video_rel)
            ).options(
                joinedload(VideoInstance.video_channel)
            ).filter(
                Video.visible == True, Channel.public == True
            )

            total = query.count()
            print 'importing {} videos'.format(total)
            start = time.time()
            done = 1

            ev = ESVideo.inserter(bulk=True)
            for v in query.yield_per(6000):
                mapped = ESVideoAttributeMap(v)
                rep = dict(
                    id=mapped.id,
                    public=mapped.public,
                    video=mapped.video,
                    title=mapped.title,
                    channel=mapped.channel,
                    category=mapped.category,
                    date_added=mapped.date_added,
                    position=mapped.position,
                    locales=mapped.locales,
                    recent_user_stars=mapped.recent_user_stars(empty=True),
                    country_restriction=mapped.country_restriction(empty=True),
                    child_instance_count=mapped.child_instance_count
                )
                ev.manager.indexer.insert(v.id, rep)

                self.print_percent_complete(done, total)
                done += 1

            ev.flush_bulk()
            print 'finished in', time.time() - start, 'seconds'

    def import_dolly_video_owners(self):
        """ Import all the owner attributes of
            a video instance belonging to a channel """

        from rockpack.mainsite.services.video.models import Channel

        with app.test_request_context():
            channels = Channel.query.options(
                joinedload(Channel.owner_rel)
            ).options(
                joinedload(Channel.video_instances)
            ).filter(
                Channel.public == True,
                Channel.visible == True,
                Channel.deleted == False)

            total = channels.count()
            done = 1

            for channel in channels.yield_per(6000):
                for video in channel.video_instances:
                    mapped = ESVideoAttributeMap(video)
                    ec = ESVideo.updater(bulk=True)
                    ec.set_document_id(video.id)
                    ec.add_field('owner', mapped.owner)
                    ec.add_field('channel_title', mapped.channel_title)
                    ec.update()
                self.print_percent_complete(done, total)
                done += 1
            self.conn.flush_bulk(forced=True)

    def import_dolly_repin_counts(self):
        from rockpack.mainsite.services.video.models import VideoInstance

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
            ).group_by(VideoInstance.id, VideoInstance.video, child.source_channel)

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

                self.print_percent_complete(done, total)
                done += 1

            total = len(instance_counts)
            done = 1

            for (_id, video), count in instance_counts.iteritems():
                ec = ESVideo.updater(bulk=True)
                ec.set_document_id(_id)
                ec.add_field('child_instance_count', count)
                ec.add_field('most_influential', True if influential_index.get(video, '')[0] == _id else False)
                ec.update()

                self.print_percent_complete(done, total)
                done += 1

            ESVideo.flush()

    def import_video_stars(self):
        from rockpack.mainsite.services.user.models import UserActivity

        with app.test_request_context():
            query = UserActivity.query.filter(
                UserActivity.action == 'star',
                UserActivity.object_type == 'video_instance'
            ).order_by(
                'object_id', 'date_actioned desc'
            )

            total = query.count()
            missing = 0
            done = 1
            start = time.time()
            for instance_id, group in groupby(query.yield_per(200).values(UserActivity.object_id, UserActivity.user), lambda x: x[0]):
                try:
                    ec = ESVideo.updater(bulk=True)
                    ec.set_document_id(instance_id)
                    ec.add_field(
                        'recent_user_stars',
                        str(list(set([u.encode('utf8') for v, u in group]))[:5])
                    )
                    ec.update()
                except ElasticSearchException:
                    missing += 1
                done += 1
                self.print_percent_complete(done, total)

            self.conn.flush_bulk(forced=True)
            print '%s finished in' % total, time.time() - start, 'seconds (%s videos not in es)' % missing

    def import_video_restrictions(self):
        from rockpack.mainsite.services.video.models import VideoRestriction, VideoInstance, Video, Channel

        with app.test_request_context():
            query = VideoRestriction.query.join(
                VideoInstance,
                VideoInstance.video == VideoRestriction.video
            ).join(Channel, VideoInstance.channel == Channel.id).join(Video, Video.id == VideoRestriction.video).filter(Video.visible == True, Channel.public == True).order_by(VideoInstance.id)

            potential = VideoInstance.query.join(Channel, VideoInstance.channel == Channel.id).join(Video, Video.id == VideoInstance.video).filter(Video.visible == True, Channel.public == True).count()

            indexing = Indexing()
            total = 0
            missing = 0
            start = time.time()
            print '2 passes for (approx) %d videos ...' % potential
            for relationship in ('allow', 'deny',):
                for instance_id, group in groupby(query.filter(VideoRestriction.relationship == relationship).yield_per(6000).values(VideoInstance.id, VideoRestriction.country), lambda x: x[0]):
                    countries = [c.encode('utf8') for i, c in group]

                    try:
                        self.conn.partial_update(
                            indexing.indexes['video']['index'],
                            indexing.indexes['video']['type'],
                            instance_id,
                            "ctx._source.country_restriction.%s = %s" % (relationship, str(countries),)
                        )
                    except ElasticSearchException, e:
                        missing += 1

                    total += 1
                print total, 'completed in this pass'
                sys.stdout.flush()
                self.conn.flush_bulk(forced=True)
            print '%s finished in' % total, time.time() - start, 'seconds (%s videos not in es)' % missing

    def _partial_update(self, index, id, script, params=None):
        self.conn.update(
            self.indexing.indexes[index]['index'],
            self.indexing.indexes[index]['type'],
            id,
            script=script,
            bulk=True
        )

    def import_video_channel_terms(self):
        from rockpack.mainsite.services.video.models import VideoInstance, Channel, Video

        query = VideoInstance.query.join(
            Channel,
            Channel.id == VideoInstance.channel
        ).join(
            Video,
            Video.id == VideoInstance.video
        ).filter(Channel.public == True, Channel.deleted == False)

        channel_terms = {}

        total = 0
        start = time.time()

        print 'Building data ...'
        for v in query.yield_per(600):
            channel_terms.setdefault(v.channel, []).append(v.video_rel.title)

        print 'Updating records in es ...'
        for c_id, terms_list in channel_terms.iteritems():
            try:
                self._partial_update(
                    'channel',
                    c_id,
                    'ctx._source.video_terms = %s' % json.dumps(terms_list)
                )
            except ElasticSearchException, e:
                print e
            total += 1

        self.conn.flush_bulk(forced=True)
        print '%s finished in' % total, time.time() - start, 'seconds'

    def import_channel_share(self):
        from rockpack.mainsite.services.share.models import ShareLink
        from rockpack.mainsite.services.user.models import UserActivity, User
        from rockpack.mainsite.services.video.models import VideoInstance, Channel

        total = 0
        missing = 0
        start = time.time()

        def _normalised(val, max_val, min_val):
            if val == min_val or val == 0:
                return 0
            return (val - min_val) / (abs(max_val) - abs(min_val))

        def _update_channel_id(id, val, max_val, min_val):
            print id, channel_dict.get(id), channel_dict.setdefault(id, 0), _normalised(val, max_val, min_val)
            channel_dict[id] = channel_dict.setdefault(id, 0) + _normalised(val, max_val, min_val)

        # The strength of actions decay until any older than zulu have no effect
        zulu = datetime.now() - timedelta(days=app.config.get('CHANNEL_RANK_ZULU', 1))
        time_since_zulu = (datetime.utcnow() - zulu).total_seconds()

        for locale in ['en-gb', 'en-us']:
            print 'starting for', locale
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

            print 'user activity done'

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

            print 'channel shares done'

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
                channel_dict[id]['norm_share_link_channel'] = channel_dict[id].setdefault('norm_share_link_channel', 0) + _normalised(count + val, q_max + channel_share_vals[0], q_min + channel_share_vals[1])

            print 'video shares done'

            print '... updating elasticsearch for %s ...' % locale

            done = 1
            i_total = len(channel_dict)
            for id, _dict in channel_dict.iteritems():
                try:
                    count = 0
                    for k, v in _dict.iteritems():
                        if k.startswith('norm'):
                            count += v

                    if count == 0:
                        continue

                    ec = ESChannel.updater(bulk=True)
                    ec.set_document_id(id)
                    ec.add_field('normalised_rank[\'%s\']' % locale, float(count))
                    ec.update()

                except exceptions.DocumentMissingException, e:
                    missing += 1
                total += 1
                self.print_percent_complete(done, i_total)
                done += 1
            ec.flush_bulk()

        print '%s total updates in two passesfinished in' % total, time.time() - start, 'seconds (%s channels not in es)' % missing
