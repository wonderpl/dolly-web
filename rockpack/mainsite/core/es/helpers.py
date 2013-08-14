import time
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
            for v in query.yield_per(6000):
                api.add_video_to_index(v, bulk=True, refresh=False, no_check=True, update_restrictions=False)
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
        from rockpack.mainsite.services.video.models import VideoRestriction, VideoInstance
        with app.test_request_context():
            query = VideoRestriction.query.join(
                VideoInstance,
                VideoInstance.video == VideoRestriction.video
            ).order_by(VideoInstance.id)

            indexing = Indexing()
            total = 0
            missing = 0
            start = time.time()
            for relationship in ('allow', 'deny',):
                for instance_id, group in groupby(query.filter(VideoRestriction.relationship == relationship).yield_per(200).values(VideoInstance.id, VideoRestriction.country), lambda x: x[0]):
                    countries = [c.encode('utf8') for i, c in group]

                    try:
                        print instance_id, 'with relationship', relationship, 'for', countries
                        self.conn.partial_update(
                            indexing.indexes['video']['index'],
                            indexing.indexes['video']['type'],
                            instance_id,
                            "ctx._source.country_restriction.%s = %s" % (relationship, str(countries),)
                        )
                    except ElasticSearchException, e:
                        print e
                        missing += 1

                self.conn.flush_bulk(forced=True)
            print '%s finished in' % total, time.time() - start, 'seconds (%s videos not in es)' % missing
