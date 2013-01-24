from datetime import datetime
from sqlalchemy import (
    Text,
    String,
    Column,
    Boolean,
    Integer,
    ForeignKey,
    event,
    DateTime,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship, aliased
from rockpack.mainsite.helpers.db import UTC
from rockpack.mainsite.helpers.db import add_base64_pk
from rockpack.mainsite.helpers.db import add_video_pk
from rockpack.mainsite.helpers.db import add_video_meta_pk
from rockpack.mainsite.core.dbapi import Base, session
from rockpack.mainsite.auth.models import User
from rockpack.mainsite.core import s3


class Locale(Base):

    __tablename__ = 'locale'

    id = Column(String(5), primary_key=True)
    name = Column(String(32))

    video_locale_meta = relationship('VideoLocaleMeta', backref='locales')

    def __unicode__(self):
        return self.name

    @classmethod
    def get_form_choices(cls):
        return session.query(cls.id, cls.name)


class Category(Base):
    """ Categories for each `locale` """

    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    name = Column(String(32))
    priority = Column(Integer, default=0)

    parent = Column(ForeignKey('category.id'), nullable=True)
    locale = Column(ForeignKey('locale.id'))

    parent_category = relationship('Category', remote_side=[id], backref='children')
    locales = relationship('Locale', backref='categories')

    video_locale_metas = relationship('VideoLocaleMeta', backref='category_ref')
    channel_locale_metas = relationship('ChannelLocaleMeta', backref='category_ref')
    external_category_maps = relationship('ExternalCategoryMap', backref='category_ref')

    def __unicode__(self):
        return self.name

    @classmethod
    def get_form_choices(cls, locale):
        query = session.query(cls.id, cls.name, ParentCategory.name).\
            filter(cls.parent == ParentCategory.id).\
            filter(cls.locale == locale)
        for id, name, parent in query:
            yield id, '%s - %s' % (parent, name)


class CategoryMap(Base):
    """ Mapping between localised categories """

    __tablename__ = 'category_locale'

    id = Column(Integer, primary_key=True)

    here = Column(ForeignKey('category.id'))
    there = Column(ForeignKey('category.id'))

    category_here = relationship('Category', foreign_keys=[here])
    category_there = relationship('Category', foreign_keys=[there])

    def __unicode__(self):
        return '{} translates to {}'.format(
               ':'.join([self.here.name, self.here.locale]),
               ':'.join([self.there.name, self.there.locale]),)


class ExternalCategoryMap(Base):

    __tablename__ = 'external_category_map'

    id = Column(Integer, primary_key=True)
    term = Column(String(32))
    label = Column(String(64), nullable=True)
    locale = Column(String(16), ForeignKey('locale.id'))
    category = Column(Integer, ForeignKey('category.id'))
    source = Column(Integer, ForeignKey('source.id'))


class Source(Base):
    __tablename__ = 'source'

    id = Column(Integer, primary_key=True)
    label = Column(String(16))
    player_template = Column(Text)

    external_category_maps = relationship('ExternalCategoryMap', backref='sources')
    video = relationship('Video', backref='sources')

    def __unicode__(self):
        return self.label

    @classmethod
    def get_form_choices(cls):
        return session.query(cls.id, cls.label)


class Video(Base):
    """ Canonical reference to a video """

    __tablename__ = 'video'

    id = Column(String(40), primary_key=True)
    title = Column(String(1024), nullable=True)
    source_videoid = Column(String(128))
    source_listid = Column(String(128), nullable=True)
    date_added = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    date_updated = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    duration = Column(Integer, default=0)
    star_count = Column(Integer, default=0)
    rockpack_curated = Column(Boolean, default=False)

    source = Column(ForeignKey('source.id'), nullable=False)

    thumbnails = relationship('VideoThumbnail', backref='video_rel')
    metas = relationship('VideoLocaleMeta', backref='video_rel')
    instances = relationship('VideoInstance', backref='video_rel')
    restrictions = relationship('VideoRestriction', backref='videos')

    def __str__(self):
        return self.title

    @property
    def default_thumbnail(self):
        for thumb in self.thumbnails:
            if 'default.jpg' in thumb.url:
                return thumb.url

    @property
    def player_link(self):
        # TODO: Use data from source
        return 'http://www.youtube.com/watch?v=' + self.source_videoid

    @classmethod
    def add_videos(cls, videos, source, locale, category):
        count = len(videos)
        for video in videos:
            video.source = source
            video.metas = [VideoLocaleMeta(locale=locale, category=category)]

        try:
            # First try to add all...
            with session.begin_nested():
                session.add_all(videos)
        except IntegrityError:
            # Else explicitly check which videos already exist
            all_ids = set(v.id for v in videos)
            query = session.query(Video.id).filter(Video.id.in_(all_ids))
            existing_ids = set(v.id for v in query)
            new_ids = all_ids - existing_ids
            session.add_all(v for v in videos if v.id in new_ids)
            count = len(new_ids)

        return count


class VideoLocaleMeta(Base):

    __tablename__ = 'video_locale_meta'

    id = Column(String(40), primary_key=True)

    video = Column(String(40), ForeignKey('video.id'))
    locale = Column(ForeignKey('locale.id'))
    category = Column(ForeignKey('category.id'))
    star_count = Column(Integer, default=0)


class VideoRestriction(Base):

    __tablename__ = 'video_restriction'

    id = Column(String(24), primary_key=True)
    video = Column(String(40), ForeignKey('video.id'))
    relationship = Column(String(16))
    country = Column(String(8))


class VideoInstance(Base):
    """ An instance of a video, which can belong to many channels """

    __tablename__ = 'video_instance'

    id = Column(String(24), primary_key=True)
    date_added = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    video = Column(String(40), ForeignKey('video.id'))
    channel = Column(String(32), ForeignKey('channel.id'))

    @property
    def default_thumbnail(self):
        return self.video_rel.default_thumbnail

    @property
    def player_link(self):
        return self.video_rel.player_link

    def __unicode__(self):
        return self.video


class VideoThumbnail(Base):

    __tablename__ = 'video_thumbnail'

    id = Column(String(24), primary_key=True)
    url = Column(String(1024))
    width = Column(Integer)
    height = Column(Integer)

    video = Column(String(40), ForeignKey('video.id'))

    def __unicode__(self):
        return '({}x{}) {}'.format(self.width, self.height, self.url)


class Channel(Base):
    """ A channel, which can contain many videos """

    __tablename__ = 'channel'

    id = Column(String(24), primary_key=True)
    title = Column(String(1024))
    thumbnail_url = Column(Text, nullable=True)

    owner = Column(String(24), ForeignKey('user.id'))
    owner_rel = relationship(User, primaryjoin=(owner == User.id))

    video_instances = relationship('VideoInstance', backref='video_channel')
    channel_locale_metas = relationship('ChannelLocaleMeta', backref='meta_parent')

    def __unicode__(self):
        return self.title

    @classmethod
    def get_form_choices(cls, owner):
        return session.query(cls.id, cls.title).filter_by(owner=owner)

    @property
    def thumbnail_url_full(self):
        if self.thumbnail_url:
            return s3.full_thumbnail_path(self.thumbnail_url)
        return ''

    def add_videos(self, videos):
        for video in videos:
            self.video_instances.append(VideoInstance(video=video.id))
        return self.save()


class ChannelLocaleMeta(Base):

    __tablename__ = 'channel_locale_meta'

    id = Column(String(24), primary_key=True)

    channel = Column(ForeignKey('channel.id'))
    locale = Column(ForeignKey('locale.id'))
    category = Column(ForeignKey('category.id'), nullable=True)

    channel_locale = relationship('Locale', remote_side=[Locale.id], backref='channel_locale_meta')

    def __unicode__(self):
        return self.locale, 'for channel', self.channel


ParentCategory = aliased(Category)


event.listen(Video, 'before_insert', add_video_pk)
event.listen(VideoLocaleMeta, 'before_insert', add_video_meta_pk)
event.listen(VideoInstance, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='vi'))
event.listen(VideoRestriction, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='vr'))
event.listen(VideoThumbnail, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='vt'))
event.listen(Channel, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='ch'))
event.listen(ChannelLocaleMeta, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='cl'))
