import sys
import time
import datetime
from decimal import Decimal
from itertools import groupby
from . import api
from . import mappings

from rockpack.mainsite import app
from rockpack.mainsite.core.es import es_connection


class Indexing(object):

    def __init__(self):
        self.conn = es_connection

        self.indexes = {
            'channel': {
                'index': mappings.CHANNEL_INDEX,
                'type': mappings.CHANNEL_TYPE,
                'mapping': mappings.channel_mapping
            },
            'video': {
                'index': mappings.VIDEO_INDEX,
                'type': mappings.VIDEO_TYPE,
                'mapping': mappings.video_mapping
            },
            'user': {
                'index': mappings.USER_INDEX,
                'type': mappings.USER_TYPE,
                'mapping': mappings.user_mapping
            },
        }

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

    def import_users(self):
        from rockpack.mainsite.services.user import models
        with app.test_request_context():
            users = models.User.query
            total = users.count()
            print 'importing {} users'.format(total)
            start = time.time()
            for users in users.yield_per(6000):
                api.add_user_to_index(users, bulk=True, refresh=False, no_check=True)
            self.conn.flush_bulk(forced=True)
            print 'finished in', time.time() - start, 'seconds'

    def import_channels(self):
        from rockpack.mainsite.services.video.models import Channel
        from sqlalchemy.orm import joinedload
        with app.test_request_context():
            channels = Channel.query.filter(
                Channel.public == True,
                Channel.deleted == False).options(
                    joinedload(Channel.category_rel), joinedload(Channel.metas), joinedload(Channel.owner_rel)
                )
            print 'importing {} PUBLIC channels\r'.format(channels.count())
            start = time.time()
            for channel in channels.yield_per(6000):
                api.add_channel_to_index(channel, bulk=True, refresh=False, no_check=True)
            self.conn.flush_bulk(forced=True)
            print 'finished in', time.time() - start, 'seconds'

    def print_percent_complete(self, current, done, total):
        n = round(done/total*100, 1)
        if n != current:
            print n, "percent complete                                                \r",
            sys.stdout.flush()
        return n

    def import_videos(self):
        from rockpack.mainsite.services.video.models import Channel, Video, VideoInstanceLocaleMeta, VideoInstance
        from sqlalchemy.orm import joinedload

        with app.test_request_context():
            query = VideoInstance.query.join(
                Channel, Video).outerjoin(
                    VideoInstanceLocaleMeta,
                    VideoInstance.id == VideoInstanceLocaleMeta.video_instance
                ).options(
                    joinedload(VideoInstance.metas)
                ).options(
                    joinedload(VideoInstance.video_rel)
                ).options(
                    joinedload(VideoInstance.video_channel)
                ).filter(Video.visible == True, Channel.public == True)

            total = query.count()
            print 'importing {} videos'.format(total)
            start = time.time()
            floated = float(total)
            cur = 0
            done = 1

            offset = 0
            bulk_size = 2000
            for v in query.yield_per(6000):
                api.add_video_to_index(v, bulk=True, refresh=False, no_check=True, update_restrictions=False, update_recentstars=False)
                cur = self.print_percent_complete(cur, done, floated)
                done += 1
            """
            while True:
                repeat = False
                for v in query.offset(offset).limit(bulk_size):#.yield_per(2000):
                    api.add_video_to_index(v, bulk=True, refresh=False, no_check=True, update_restrictions=False, update_recentstars=False)
                    cur = self.print_percentage_complete(cur, floated)
                    repeat = True

                time.sleep(2)
                offset += bulk_size
                print 'next batch                       /r',
                sys.stdout.flush()

                if not repeat:
                    break
            """
            self.conn.flush_bulk(forced=True)
            print 'finished in', time.time() - start, 'seconds'

    def import_video_stars(self):
        from pyes.exceptions import ElasticSearchException
        from rockpack.mainsite.services.user.models import UserActivity
        with app.test_request_context():
            query = UserActivity.query.filter(
                UserActivity.action == 'star',
                UserActivity.object_type == 'video_instance'
            ).order_by(
                'object_id', 'date_actioned desc'
            )

            indexing = Indexing()
            total = 0
            missing = 0
            start = time.time()
            for instance_id, group in groupby(query.yield_per(200).values(UserActivity.object_id, UserActivity.user), lambda x: x[0]):
                try:
                    self.conn.partial_update(
                        indexing.indexes['video']['index'],
                        indexing.indexes['video']['type'],
                        instance_id,
                        "ctx._source.recent_user_stars = %s" % str(
                            list(set([u.encode('utf8') for v, u in group]))[:5]
                        )
                    )
                except ElasticSearchException:
                    missing += 1

            self.conn.flush_bulk(forced=True)
            print '%s finished in' % total, time.time() - start, 'seconds (%s videos not in es)' % missing

    def import_video_restrictions(self):
        from pyes.exceptions import ElasticSearchException
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

    def _partial_update(self, index, id, script):
        self.conn.partial_update(
            self.indexing.indexes[index]['index'],
            self.indexing.indexes[index]['type'],
            id,
            script
        )

    def import_channel_share(self):
        from pyes.exceptions import ElasticSearchException
        from rockpack.mainsite.services.share.models import ShareLink
        from rockpack.mainsite.services.user.models import UserActivity, User
        from rockpack.mainsite.services.video.models import VideoInstance, Channel
        from sqlalchemy import distinct, func

        from rockpack.mainsite.core.dbapi import db

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

        zulu = datetime.datetime(2013, 06, 26)
        time_since_zulu = (datetime.datetime.utcnow() - zulu).total_seconds()

        for locale in ['en-gb', 'en-us']:
            print 'starting for', locale
            channel_dict = {}
            channel_shares = {}

            summation = func.sum(
                (time_since_zulu - (func.extract('epoch', datetime.datetime.utcnow()) - func.extract('epoch', UserActivity.date_actioned))) / time_since_zulu
            )

            # activity for channels from videos
            query = db.session.query(
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
                (time_since_zulu - (func.extract('epoch', datetime.datetime.utcnow()) - func.extract('epoch', ShareLink.date_created))) / time_since_zulu
            )

            # activity for channel shares
            query = db.session.query(
                distinct(Channel.id).label('channel_id'),
                summation.label('summed')
            ).join(
                ShareLink,
                ShareLink.object_id == Channel.id
            ).join(
                User, User.id == ShareLink.user
            ).filter(
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
            query = db.session.query(
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
            for id, _dict in channel_dict.iteritems():
                try:
                    #print 'inserting', _dict, 'in to', id
                    count = 0
                    u_strings = []

                    for k, v in _dict.iteritems():
                        if k.startswith('norm'):
                            count += v
                        else:
                            u_strings.append('ctx._source.%s = %s' % (k, map(lambda x: Decimal.to_eng_string(x) if x else 0, v),))

                    u_strings.append('ctx._source.normalised_rank[\'%s\'] = %f' % (locale, float(count),))

                    if count > 0:
                        self._partial_update('channel', id, ';'.join(u_strings))
                except ElasticSearchException, e:
                    missing += 1
                total += 1

        self.conn.flush_bulk(forced=True)

        print '%s finished in' % total, time.time() - start, 'seconds (%s channels not in es)' % missing
