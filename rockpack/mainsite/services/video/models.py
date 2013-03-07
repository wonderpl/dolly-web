from sqlalchemy import (
    Text, String, Column, Boolean, Integer, ForeignKey, DateTime, CHAR,
    UniqueConstraint, event, func)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship, aliased
from rockpack.mainsite.core.dbapi import db
from rockpack.mainsite.helpers.db import (
    add_base64_pk, add_video_pk, add_video_meta_pk,
    gen_videoid, insert_new_only, ImageType)
from rockpack.mainsite.helpers.urls import url_for
from rockpack.mainsite.services.user.models import User
from rockpack.mainsite import app


class Locale(db.Model):

    __tablename__ = 'locale'

    id = Column(String(16), primary_key=True)
    name = Column(String(32), unique=True, nullable=False)

    def __unicode__(self):
        return self.name

    @classmethod
    def get_form_choices(cls):
        return cls.query.values(cls.id, cls.name)


class Category(db.Model):
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
    def map_to(cls, category, locale):
        """Return the equivalent category for the given locale"""
        map = lambda here, there: cls.query.join(
            CategoryMap, (there == cls.id) & (cls.locale == locale)).\
            filter(here == category).value(there)
        return map(CategoryMap.here, CategoryMap.there) or \
            map(CategoryMap.there, CategoryMap.here)

    @classmethod
    def get_default_category_id(cls, locale):
        # TODO: cache/memoize
        return cls.query.filter_by(locale=locale, name='Other', parent=None).value('id')

    @classmethod
    def get_form_choices(cls, locale):
        query = cls.query.filter_by(parent=ParentCategory.id, locale=locale).\
            values(cls.id, cls.name, ParentCategory.name)
        for id, name, parent in query:
            yield id, '%s - %s' % (parent, name)


class CategoryMap(db.Model):
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


class ExternalCategoryMap(db.Model):

    __tablename__ = 'external_category_map'
    __table_args__ = (
        UniqueConstraint('locale', 'source', 'term'),
    )

    id = Column(Integer, primary_key=True)
    term = Column(String(32), nullable=False)
    label = Column(String(32), nullable=False)
    locale = Column(ForeignKey('locale.id'), nullable=False)
    category = Column(ForeignKey('category.id'), nullable=True)
    source = Column(ForeignKey('source.id'), nullable=False)


class Source(db.Model):
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
        return cls.query.values(cls.id, cls.label)


class Video(db.Model):
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
    view_count = Column(Integer, nullable=False, server_default='0')
    star_count = Column(Integer, nullable=False, server_default='0')
    rockpack_curated = Column(Boolean, nullable=False, server_default='false', default=False)

    source = Column(ForeignKey('source.id'), nullable=False)

    thumbnails = relationship('VideoThumbnail', backref='video_rel',
                              lazy='joined', passive_deletes=True,
                              cascade="all, delete-orphan")
    metas = relationship('VideoLocaleMeta', backref='video_rel')
    instances = relationship('VideoInstance', backref=db.backref('video_rel', lazy='joined'),
                             passive_deletes=True, cascade="all, delete-orphan")
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

    def add_meta(self, locale):
        # Try mapping category from existing meta record to new locale
        category = VideoLocaleMeta.query.filter_by(video=self.id).value('category')
        if category:
            category = Category.map_to(category, locale)
        # Else fall back on default "Other"
        else:
            category = Category.get_default_category_id(locale)
        meta = VideoLocaleMeta(locale=locale, category=category)
        self.metas.append(meta)
        self.save()
        return meta

    @classmethod
    def add_videos(cls, videos, source, locale, category=None):
        if not category:
            category = Category.get_default_category_id(locale)
        for video in videos:
            video.source = source
            video.metas = [VideoLocaleMeta(locale=locale, category=category)]

        session = cls.query.session
        try:
            # First try to add all...
            with session.begin_nested():
                session.add_all(videos)
            count = len(videos)
        except IntegrityError:
            # Else explicitly check which videos already exist
            new_ids, existing_ids = insert_new_only(Video, videos)
            # New metadata records may be needed for this locale
            metas = [VideoLocaleMeta(
                     id=gen_videoid(locale, source, video.source_videoid),
                     video=video.id, locale=locale, category=category)
                     for video in videos if video.id in existing_ids]
            insert_new_only(VideoLocaleMeta, metas)
            count = len(new_ids)

        return count


class VideoLocaleMeta(db.Model):

    __tablename__ = 'video_locale_meta'
    __table_args__ = (
        UniqueConstraint('locale', 'video'),
    )

    id = Column(CHAR(40), primary_key=True)

    video = Column(ForeignKey('video.id', ondelete='CASCADE'), nullable=False)
    locale = Column(ForeignKey('locale.id'), nullable=False)
    category = Column(ForeignKey('category.id'), nullable=False)
    visible = Column(Boolean(), nullable=False, server_default='true', default=True)
    view_count = Column(Integer, nullable=False, server_default='0')
    star_count = Column(Integer, nullable=False, server_default='0')

    locale_rel = relationship('Locale', backref='videolocalemetas')


class VideoRestriction(db.Model):

    __tablename__ = 'video_restriction'

    id = Column(CHAR(24), primary_key=True)
    video = Column(ForeignKey('video.id'), nullable=False, index=True)
    relationship = Column(String(16), nullable=False)
    country = Column(String(16), nullable=False)


class VideoInstance(db.Model):
    """ An instance of a video, which can belong to many channels """

    __tablename__ = 'video_instance'
    __table_args__ = (
        UniqueConstraint('channel', 'video'),
    )

    id = Column(CHAR(24), primary_key=True)
    date_added = Column(DateTime(timezone=True), nullable=False, default=func.now())
    view_count = Column(Integer, nullable=False, server_default='0')
    star_count = Column(Integer, nullable=False, server_default='0')

    video = Column(ForeignKey('video.id', ondelete='CASCADE'), nullable=False)
    channel = Column(ForeignKey('channel.id'), nullable=False)

    @property
    def default_thumbnail(self):
        return self.video_rel.default_thumbnail

    @property
    def player_link(self):
        return self.video_rel.player_link

    def __unicode__(self):
        return self.video


class VideoThumbnail(db.Model):

    __tablename__ = 'video_thumbnail'

    id = Column(CHAR(24), primary_key=True)
    url = Column(String(1024), nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)

    video = Column(ForeignKey('video.id', ondelete='CASCADE'), nullable=False, index=True)

    def __unicode__(self):
        return '({}x{}) {}'.format(self.width, self.height, self.url)


class Channel(db.Model):
    """ A channel, which can contain many videos """

    __tablename__ = 'channel'
    __table_args__ = (
        UniqueConstraint('owner', 'title'),
    )

    id = Column(CHAR(24), primary_key=True)
    title = Column(String(1024), nullable=False)
    description = Column(Text, nullable=False)
    cover = Column(ImageType('CHANNEL', reference_only=True), nullable=False)
    public = Column(Boolean(), nullable=False, server_default='true', default=True)

    owner = Column(CHAR(22), ForeignKey('user.id'), nullable=False)
    owner_rel = relationship(User, primaryjoin=(owner == User.id), lazy='joined', innerjoin=True)

    video_instances = relationship('VideoInstance', backref='video_channel')
    metas = relationship('ChannelLocaleMeta', backref=db.backref('channel_rel', lazy='joined', innerjoin=True))

    def __unicode__(self):
        return self.title

    @classmethod
    def get_form_choices(cls, owner):
        return cls.query.filter_by(owner=owner).values(cls.id, cls.title)

    @classmethod
    def channelmeta_for_category(cls, category, locale):
        if locale is None:
            locale = Category.query.filter_by(id=category).value('locale')
        return [ChannelLocaleMeta(
            locale=locale,
            category=category)]

    @classmethod
    def create(cls, category, locale=None, public=True, **kwargs):
        """Create & save a new channel record along with appropriate category metadata"""
        channel = Channel(**kwargs)
        channel.public = channel.should_be_public(channel, public)
        if category:
            channel.metas = cls.channelmeta_for_category(category, locale)
        return channel.save()

    def get_resource_url(self, own=False):
        view = 'userws.owner_channel_info' if own else 'userws.channel_info'
        return url_for(view, userid=self.owner_rel.id, channelid=self.id)
    resource_url = property(get_resource_url)

    def add_videos(self, videos):
        instances = [VideoInstance(channel=self.id, video=getattr(v, 'id', v)) for v in videos]
        session = self.query.session
        try:
            with session.begin_nested():
                session.add_all(instances)
        except IntegrityError:
            existing = [i.video for i in session.query(VideoInstance.video).
                        filter_by(channel=self.id).
                        filter(VideoInstance.video.in_(set(i.video for i in instances)))]
            session.add_all(i for i in instances if i.video not in existing)

    def remove_videos(self, videos):
        VideoInstance.query.filter_by(channel=self.id).filter(
            VideoInstance.video.in_(set(getattr(v, 'id', v) for v in videos))).\
            delete(synchronize_session=False)

    @classmethod
    def should_be_public(self, channel, public):
        """ Return False if conditions for
            visibility are not met """
        if not (channel.description and channel.cover and
                (channel.title and not channel.title.startswith(app.config['UNTITLED_CHANNEL']))):
            return False

        return public


class ChannelLocaleMeta(db.Model):

    __tablename__ = 'channel_locale_meta'
    __table_args__ = (
        UniqueConstraint('locale', 'channel'),
    )

    id = Column(CHAR(24), primary_key=True)
    visible = Column(Boolean(), nullable=False, server_default='true', default=True)
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


@event.listens_for(ChannelLocaleMeta, 'before_update')
def _update_video_visibility(mapper, connection, target):
    # If a channel is marked invisible then mark all the videos it references too
    # XXX: We probably want to remove this again before launch because a video
    # can be in many channels
    if not target.visible:
        VideoLocaleMeta.query.\
            filter_by(locale=target.locale).\
            filter(VideoLocaleMeta.video.in_(
                VideoInstance.query.filter_by(channel=target.channel).\
                    with_entities(VideoInstance.video)
            )).update(dict(visible=target.visible), False)

event.listen(Video, 'before_insert', add_video_pk)
event.listen(VideoLocaleMeta, 'before_insert', add_video_meta_pk)
event.listen(VideoInstance, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='vi'))
event.listen(VideoRestriction, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='vr'))
event.listen(VideoThumbnail, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='vt'))
event.listen(Channel, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='ch'))
event.listen(ChannelLocaleMeta, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='cl'))
