import sys
from . import api
from . import mappings

from rockpack.mainsite import app
from rockpack.mainsite.core.es import get_es_connection


class Indexing(object):

    def __init__(self):
        self.conn = get_es_connection()

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
        app.logger.debug('deleting {} index {}'.format(index, self.indexes[index]['index']))
        self.conn.indices.delete_index_if_exists(self.indexes[index]['index'])

    def create_index(self, index, rebuild=False):
        if rebuild:
            self.delete_index(index)
        app.logger.debug('creating {} index {}'.format(index, self.indexes[index]['index']))
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
        self.conn = get_es_connection()

    def import_owners(self):
        from rockpack.mainsite.services.user import models
        with app.test_request_context():
            app.logger.info('importing owners')
            for user in models.User.query.all():
                sys.stdout.write('.')
                sys.stdout.flush()
                self.conn.index(
                    {
                        'id': user.id,
                        'avatar_thumbnail': user.avatar.thumbnail_small,
                        'resource_url': user.get_resource_url(False),
                        'display_name': user.display_name,
                        'name': user.username
                    },
                    mappings.USER_INDEX,
                    mappings.USER_TYPE,
                    id=user.id)

    def import_channels(self):
        from rockpack.mainsite.services.video.models import Category, Channel, _locale_dict_from_object

        cat_map = {c[0]: c[1] for c in Category.query.filter(Category.parent != None).values('id', 'parent')}

        with app.test_request_context():
            app.logger.info('importing channels')
            for i, channel in enumerate(Channel.query.filter(Channel.public == True)):
                sys.stdout.write('.')
                sys.stdout.flush()
                try:
                    category = [channel.category, cat_map[channel.category]] if channel.category else []
                except KeyError:
                    category = [channel.category]
                data = {
                    'id': channel.id,
                    'locale': _locale_dict_from_object(channel.metas),
                    'subscriber_count': channel.subscriber_count,
                    'category': category,
                    'description': channel.description,
                    'thumbnail_url': channel.cover.thumbnail_large,
                    'cover_thumbnail_small_url': channel.cover.thumbnail_small,
                    'cover_thumbnail_large_url': channel.cover.thumbnail_large,
                    'cover_background_url': channel.cover.background,
                    'resource_url': channel.get_resource_url(),
                    'date_added': channel.date_added,
                    'title': channel.title,
                    'owner_id': channel.owner,
                    'ecommerce_url': channel.ecommerce_url
                }
                api.add_channel_to_index(self.conn, data)

    def import_videos(self):
        from rockpack.mainsite.services.video.models import Category, Channel, Video, VideoInstance, _locale_dict_from_object
        cat_map = {c[0]: c[1] for c in Category.query.filter(Category.parent != None).values('id', 'parent')}
        with app.test_request_context():
            query = VideoInstance.query.join(Channel, Video).filter(Video.visible == True, Channel.public == True)
            total = query.count()
            step = 400
            app.logger.info('importing videos: stepping in {}s of {}'.format(step, total))
            for i in xrange(0, total, step):
                sys.stdout.write('.')
                sys.stdout.flush()
                for v in query.offset(i).limit(step):
                    api.add_video_to_index(
                        self.conn,
                        {
                            'id': v.id,
                            'channel': v.channel,
                            'locale': _locale_dict_from_object(v.metas),
                            'category': [v.category, cat_map[v.category]] if v.category else [],
                            'title': v.video_rel.title,
                            'date_added': v.date_added,
                            'position': v.position,
                            'video_id': v.video,
                            'thumbnail_url': v.video_rel.thumbnails[0].url if v.video_rel.thumbnails else '',
                            'view_count': v.video_rel.view_count,
                            'star_count': v.video_rel.star_count,
                            'source': v.video_rel.source,
                            'source_id': v.video_rel.source_videoid,
                            'duration': v.video_rel.duration,
                        }
                    )
