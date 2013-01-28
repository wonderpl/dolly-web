from sqlalchemy import (
    Text,
    String,
    Column,
    Boolean,
    Integer,
    ForeignKey,
    DateTime,
    CHAR,
    UniqueConstraint,
    event,
    func,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship, aliased
from flask import g
from flask import current_app
from rockpack.mainsite.helpers.urls import image_url_from_path
from rockpack.mainsite.helpers.db import add_base64_pk
from rockpack.mainsite.helpers.db import add_video_pk
from rockpack.mainsite.helpers.db import add_video_meta_pk
from rockpack.mainsite.core.dbapi import Base, get_session
from rockpack.mainsite.auth.models import User


class Locale(Base):

    __tablename__ = 'locale'

    id = Column(String(5), primary_key=True)
    name = Column(String(32), unique=True, nullable=False)

    video_locale_meta = relationship('VideoLocaleMeta', backref='locales')

    def __unicode__(self):
        return self.name

    @classmethod
    def get_form_choices(cls):
        return g.session.query(cls.id, cls.name)


class Category(Base):
    """ Categories for each `locale` """

    __tablename__ = 'category'
    __table_args__ = (
        UniqueConstraint('locale', 'parent', 'name'),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(32), nullable=False)
    priority = Column(Integer, nullable=False, server_default='0')

    parent = Column(ForeignKey('category.id'), nullable=True)
    locale = Column(ForeignKey('locale.id'), nullable=False)

    parent_category = relationship('Category', remote_side=[id], backref='children')
    locales = relationship('Locale', backref='categories')

    video_locale_metas = relationship('VideoLocaleMeta', backref='category_ref',
                                      passive_deletes=True)
    channel_locale_metas = relationship('ChannelLocaleMeta', backref='category_ref',
                                        passive_deletes=True)
    external_category_maps = relationship('ExternalCategoryMap', backref='category_ref')

    def __unicode__(self):
        return self.name

    @classmethod
    def get_form_choices(cls, locale):
        query = g.session.query(cls.id, cls.name, ParentCategory.name).\
            filter(cls.parent == ParentCategory.id).\
            filter(cls.locale == locale)
        for id, name, parent in query:
            yield id, '%s - %s' % (parent, name)


class CategoryMap(Base):
    """ Mapping between localised categories """

    __tablename__ = 'category_locale'
    __table_args__ = (
        UniqueConstraint('here', 'there'),
    )

    id = Column(Integer, primary_key=True)

    here = Column(ForeignKey('category.id'), nullable=False)
    there = Column(ForeignKey('category.id'), nullable=False)

    category_here = relationship('Category', foreign_keys=[here])
    category_there = relationship('Category', foreign_keys=[there])

    def __unicode__(self):
        return '{} translates to {}'.format(
               ':'.join([self.here.name, self.here.locale]),
               ':'.join([self.there.name, self.there.locale]),)


class ExternalCategoryMap(Base):

    __tablename__ = 'external_category_map'
    __table_args__ = (
        UniqueConstraint('locale', 'source', 'term'),
    )

    id = Column(Integer, primary_key=True)
    term = Column(String(32), nullable=False)
    label = Column(String(64), nullable=False)
    locale = Column(String(16), ForeignKey('locale.id'), nullable=False)
    category = Column(Integer, ForeignKey('category.id'), nullable=False)
    source = Column(Integer, ForeignKey('source.id'), nullable=False)


class Source(Base):
    __tablename__ = 'source'

    id = Column(Integer, primary_key=True)
    label = Column(String(16), unique=True, nullable=False)
    player_template = Column(Text, nullable=False)

    external_category_maps = relationship('ExternalCategoryMap', backref='sources')
    video = relationship('Video', backref='sources')

    def __unicode__(self):
        return self.label

    @classmethod
    def get_form_choices(cls):
        return g.session.query(cls.id, cls.label)


class Video(Base):
    """ Canonical reference to a video """

    __tablename__ = 'video'
    __table_args__ = (
        UniqueConstraint('source', 'source_videoid'),
    )

    id = Column(CHAR(40), primary_key=True)
    title = Column(String(1024), nullable=False)
    source_videoid = Column(String(128), nullable=False)
    source_listid = Column(String(128), nullable=True)
    date_added = Column(DateTime(timezone=True), nullable=False, default=func.now())
    date_updated = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    duration = Column(Integer, nullable=False, server_default='0')
    star_count = Column(Integer, nullable=False, server_default='0')
    rockpack_curated = Column(Boolean, nullable=False, server_default='false')

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
            with g.session.begin_nested():
                g.session.add_all(videos)
        except IntegrityError:
            # Else explicitly check which videos already exist
            all_ids = set(v.id for v in videos)
            query = g.session.query(Video.id).filter(Video.id.in_(all_ids))
            existing_ids = set(v.id for v in query)
            new_ids = all_ids - existing_ids
            g.session.add_all(v for v in videos if v.id in new_ids)
            count = len(new_ids)

        return count


class VideoLocaleMeta(Base):

    __tablename__ = 'video_locale_meta'
    __table_args__ = (
        UniqueConstraint('locale', 'video'),
    )

    id = Column(CHAR(40), primary_key=True)

    video = Column(CHAR(40), ForeignKey('video.id'), nullable=False)
    locale = Column(ForeignKey('locale.id'), nullable=False)
    category = Column(ForeignKey('category.id'), nullable=False)
    visible = Column(Boolean(), nullable=False, server_default='true')
    view_count = Column(Integer, nullable=False, server_default='0')
    star_count = Column(Integer, nullable=False, server_default='0')


class VideoRestriction(Base):

    __tablename__ = 'video_restriction'

    id = Column(String(24), primary_key=True)
    video = Column(CHAR(40), ForeignKey('video.id'), nullable=False, index=True)
    relationship = Column(String(16), nullable=False)
    country = Column(String(8), nullable=False)


class VideoInstance(Base):
    """ An instance of a video, which can belong to many channels """

    __tablename__ = 'video_instance'
    __table_args__ = (
        UniqueConstraint('channel', 'video'),
    )

    id = Column(String(24), primary_key=True)
    date_added = Column(DateTime(timezone=True), nullable=False, default=func.now())

    video = Column(CHAR(40), ForeignKey('video.id'), nullable=False)
    channel = Column(String(32), ForeignKey('channel.id'), nullable=False)

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
    url = Column(String(1024), nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)

    video = Column(CHAR(40), ForeignKey('video.id'), nullable=False, index=True)

    def __unicode__(self):
        return '({}x{}) {}'.format(self.width, self.height, self.url)


class Avatar(Base):

    __tablename__ = 'avatar'

    id = Column(String(24), primary_key=True)
    original = Column(String(1024), nullable=False)
    small = Column(String(1024), nullable=False)
    medium = Column(String(1024), nullable=False)
    large = Column(String(1024), nullable=False)

    owner = Column(String(24), ForeignKey('user.id'), nullable=False)
    user = relationship(User, primaryjoin=(owner == User.id))

    @property
    def small_url(self):
        return image_url_from_path(self.small)

    @property
    def medium_url(self):
        return image_url_from_path(self.medium)

    @property
    def large_url(self):
        return image_url_from_path(self.large)


class Channel(Base):
    """ A channel, which can contain many videos """

    __tablename__ = 'channel'
    __table_args__ = (
        UniqueConstraint('owner', 'title'),
    )

    id = Column(String(24), primary_key=True)
    title = Column(String(1024), nullable=False)

    image = Column(String(24), ForeignKey('channel_image.id'), nullable=False)

    owner = Column(String(24), ForeignKey('user.id'), nullable=False)
    owner_rel = relationship(User, primaryjoin=(owner == User.id))

    video_instances = relationship('VideoInstance', backref='video_channel')
    channel_locale_metas = relationship('ChannelLocaleMeta', backref='meta_parent')

    def __unicode__(self):
        return self.title

    @classmethod
    def get_form_choices(cls, owner):
        return g.session.query(cls.id, cls.title).filter_by(owner=owner)

    @property
    def thumbnail_url_full(self):
        return self.channel_images.thumbnail_large_url

    def add_videos(self, videos):
        for video in videos:
            self.video_instances.append(VideoInstance(video=video.id))
        return self.save()


class ChannelImage(Base):

    __tablename__ = 'channel_image'

    id = Column(CHAR(24), primary_key=True)
    name = Column(String(26), nullable=False)

    owner = Column(String(24), ForeignKey('user.id'), nullable=False)
    user = relationship(User, primaryjoin=(owner == User.id))
    channels = relationship('Channel', backref='channel_images')

    # TODO: do this smarter. looks horrible

    @property
    def original_url(self):
        return image_url_from_path(current_app.config['CHANNEL_IMG_PATHS']['original'] + self.name)

    @property
    def thumbnail_small_url(self):
        return image_url_from_path(current_app.config['CHANNEL_IMG_PATHS']['thumbnail_small'] + self.name)

    @property
    def thumbnail_large_url(self):
        return image_url_from_path(current_app.config['CHANNEL_IMG_PATHS']['thumbnail_large'] + self.name)

    @property
    def carousel_url(self):
        return image_url_from_path(current_app.config['CHANNEL_IMG_PATHS']['carousel'] + self.name)

    @property
    def cover_url(self):
        return image_url_from_path(current_app.config['CHANNEL_IMG_PATHS']['cover'] + self.name)


class ChannelLocaleMeta(Base):

    __tablename__ = 'channel_locale_meta'
    __table_args__ = (
        UniqueConstraint('locale', 'channel'),
    )

    id = Column(CHAR(24), primary_key=True)
    visible = Column(Boolean(), nullable=False, server_default='true')
    view_count = Column(Integer, nullable=False, server_default='0')
    star_count = Column(Integer, nullable=False, server_default='0')

    channel = Column(ForeignKey('channel.id'), nullable=False)
    locale = Column(ForeignKey('locale.id'), nullable=False)
    category = Column(ForeignKey('category.id'), nullable=False)

    channel_locale = relationship('Locale', remote_side=[Locale.id], backref='channel_locale_meta')

    def __unicode__(self):
        return self.locale, 'for channel', self.channel


ParentCategory = aliased(Category)


@event.listens_for(Category, 'before_insert')
def _set_child_category_locale(mapper, connection, target):
    if not target.locale and target.parent_category:
        target.locale = target.parent_category.locale


event.listen(Video, 'before_insert', add_video_pk)
event.listen(VideoLocaleMeta, 'before_insert', add_video_meta_pk)
event.listen(VideoInstance, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='vi'))
event.listen(VideoRestriction, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='vr'))
event.listen(VideoThumbnail, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='vt'))
event.listen(Channel, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='ch'))
event.listen(ChannelImage, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='ci'))
event.listen(ChannelLocaleMeta, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='cl'))
