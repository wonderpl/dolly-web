from sqlalchemy import (
    Text, String, Column, Boolean, Integer, Float, ForeignKey, DateTime, CHAR,
    UniqueConstraint, event, func)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship, aliased
from rockpack.mainsite.core.dbapi import db
from rockpack.mainsite.helpers.db import add_base64_pk, add_video_pk, insert_new_only, ImageType, BoxType
from rockpack.mainsite.helpers.urls import url_for
from rockpack.mainsite.services.user.models import User
from rockpack.mainsite import app
from rockpack.mainsite.core.es import api as es_api


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
        UniqueConstraint('name', 'parent'),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(32), nullable=False)

    parent = Column(ForeignKey('category.id'), nullable=True)

    parent_category = relationship('Category', remote_side=[id], backref='children')
    translations = relationship('CategoryTranslation', backref='category_rel')
    video_instancess = relationship('VideoInstance', backref='category_ref', passive_deletes=True)
    external_category_maps = relationship('ExternalCategoryMap', backref='category_ref')

    def __unicode__(self):
        pname = self.parent_category.name if self.parent_category else '-'
        return '{} - {}'.format(pname, self.name)

    @classmethod
    def get_form_choices(cls, locale):
        query = cls.query.filter(
            CategoryTranslation.category == Category.id,
            CategoryTranslation.locale == locale).order_by('parent asc')
        for q in query:
            pname = q.parent_category.name if q.parent_category else '-'
            yield q.id, '%s - %s' % (pname, q.name)


class CategoryTranslation(db.Model):
    __tablename__ = 'category_translation'
    __table_args__ = (
        UniqueConstraint('locale', 'category'),
    )

    id = Column(Integer, primary_key=True)
    locale = Column(ForeignKey('locale.id'), nullable=False)
    category = Column(ForeignKey('category.id'), nullable=False)
    priority = Column(Integer, nullable=False, server_default='0')
    name = Column(String(32), nullable=False)

    locale_rel = relationship('Locale', backref='categorytranslations')


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
    source = Column(ForeignKey('source.id'), nullable=False)
    source_videoid = Column(String(128), nullable=False)
    source_listid = Column(String(128), nullable=True)
    source_username = Column(String(128), nullable=True)
    date_added = Column(DateTime(), nullable=False, default=func.now())
    date_updated = Column(DateTime(), nullable=False, default=func.now(), onupdate=func.now())
    duration = Column(Integer, nullable=False, server_default='0')
    view_count = Column(Integer, nullable=False, server_default='0')
    star_count = Column(Integer, nullable=False, server_default='0')
    rockpack_curated = Column(Boolean, nullable=False, server_default='false', default=False)
    visible = Column(Boolean(), nullable=False, server_default='true', default=True)

    thumbnails = relationship('VideoThumbnail', backref='video_rel',
                              passive_deletes=True,
                              cascade="all, delete-orphan")
    instances = relationship('VideoInstance', backref=db.backref('video_rel', lazy='joined'),
                             passive_deletes=True, cascade="all, delete-orphan")
    restrictions = relationship('VideoRestriction', backref='videos',
                                cascade="all, delete-orphan", passive_deletes=True)

    def __str__(self):
        return self.title

    @property
    def default_thumbnail(self):
        # Short-circuit for youtube to avoid join:
        if self.source == 1:
            return 'http://i.ytimg.com/vi/%s/mqdefault.jpg' % self.source_videoid
        for thumb in self.thumbnails:
            if 'default.jpg' in thumb.url:
                return thumb.url

    @property
    def player_link(self):
        # TODO: Use data from source
        return 'http://www.youtube.com/watch?v=' + self.source_videoid

    @classmethod
    def add_videos(cls, videos, source):
        for video in videos:
            video.source = source
        session = cls.query.session
        try:
            # First try to add all...
            with session.begin_nested():
                session.add_all(videos)
            count = len(videos)
        except IntegrityError:
            # Else explicitly check which videos already exist
            new_ids, existing_ids = insert_new_only(Video, videos)
            count = len(new_ids)

        return count


class VideoInstanceLocaleMeta(db.Model):

    __tablename__ = 'video_instance_locale_meta'
    __table_args__ = (
        UniqueConstraint('locale', 'video_instance'),
    )

    id = Column(CHAR(24), primary_key=True)

    video_instance = Column(ForeignKey('video_instance.id', ondelete='CASCADE'), nullable=False)
    view_count = Column(Integer, nullable=False, server_default='0')
    star_count = Column(Integer, nullable=False, server_default='0')
    date_added = Column(DateTime(), nullable=False, default=func.now())
    date_updated = Column(DateTime(), nullable=False, default=func.now(), onupdate=func.now())
    locale = Column(ForeignKey('locale.id'), nullable=False)

    locale_rel = relationship('Locale', backref='videoinstancelocalemetas')


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
    date_added = Column(DateTime(), nullable=False, default=func.now())
    view_count = Column(Integer, nullable=False, server_default='0')
    star_count = Column(Integer, nullable=False, server_default='0')
    position = Column(Integer, nullable=False, server_default='0', default=0)

    video = Column(ForeignKey('video.id', ondelete='CASCADE'), nullable=False)
    channel = Column(ForeignKey('channel.id'), nullable=False)
    category = Column(ForeignKey('category.id'), nullable=True)

    metas = relationship('VideoInstanceLocaleMeta', backref='video_instance_rel', cascade='all,delete')
    category_rel = relationship('Category', backref='video_instance_rel')

    @property
    def default_thumbnail(self):
        return self.video_rel.default_thumbnail

    @property
    def player_link(self):
        return self.video_rel.player_link

    def add_meta(self, locale):
        return VideoInstanceLocaleMeta(video_instance=self.id, locale=locale).save()

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

    id = Column(CHAR(24), primary_key=True)
    title = Column(String(25), nullable=False)
    description = Column(Text(200), nullable=False)
    cover = Column(ImageType('CHANNEL', reference_only=True), nullable=False)
    cover_aoi = Column(BoxType, nullable=True)
    public = Column(Boolean(), nullable=False, server_default='true', default=True)
    verified = Column(Boolean(), nullable=False, server_default='false', default=False)
    view_count = Column(Integer, nullable=False, server_default='0', default=0)
    star_count = Column(Integer, nullable=False, server_default='0', default=0)
    subscriber_count = Column(Integer, nullable=False, server_default='0', default=0)
    date_added = Column(DateTime(), nullable=False, default=func.now())
    date_updated = Column(DateTime(), nullable=False, default=func.now(), onupdate=func.now())
    update_frequency = Column(Float, nullable=True)
    ecommerce_url = Column(String(1024), nullable=False, server_default='')
    editorial_boost = Column(Float(precision=1), nullable=True, server_default='1.0', default=1.0)
    favourite = Column(Boolean(), nullable=False, server_default='false', default=False)

    category = Column(ForeignKey('category.id'), nullable=True)
    category_rel = relationship(Category, primaryjoin=(category == Category.id), lazy='joined')

    owner = Column(CHAR(22), ForeignKey('user.id'), nullable=False, default='', server_default='')
    owner_rel = relationship(User, primaryjoin=(owner == User.id), lazy='joined', innerjoin=True)

    deleted = Column(Boolean(), nullable=False, server_default='false', default=False)

    video_instances = relationship('VideoInstance', backref='video_channel')
    metas = relationship('ChannelLocaleMeta', backref=db.backref('channel_rel', lazy='joined', innerjoin=True))

    def __unicode__(self):
        return self.title

    @classmethod
    def get_form_choices(cls, owner):
        return cls.query.filter_by(owner=owner).values(cls.id, cls.title)

    @classmethod
    def create(cls, locale=None, public=True, **kwargs):
        """Create & save a new channel record along with appropriate category metadata"""
        channel = Channel(**kwargs)
        channel.public = channel.should_be_public(channel, public)
        return channel.save()

    @classmethod
    def should_be_public(self, channel, public):
        """Return False if conditions for visibility are not met"""
        if not (channel.cover and
                (channel.title and not channel.title.startswith(app.config['UNTITLED_CHANNEL'])) and
                channel.video_instances):
            return False

        return public

    @property
    def editable(self):
        return not self.favourite

    def get_resource_url(self, own=False):
        view = 'userws.owner_channel_info' if own else 'userws.channel_info'
        return url_for(view, userid=self.owner, channelid=self.id)

    resource_url = property(get_resource_url)

    def add_videos(self, videos):
        existing_videos = bool(self.video_instances)
        instances = [VideoInstance(channel=self.id, video=getattr(v, 'id', v),
                                   category=self.category) for v in videos]
        session = self.query.session
        try:
            with session.begin_nested():
                session.add_all(instances)
        except IntegrityError:
            existing = [i.video for i in session.query(VideoInstance.video).
                        filter_by(channel=self.id).
                        filter(VideoInstance.video.in_(set(i.video for i in instances)))]
            session.add_all(i for i in instances if i.video not in existing)

        # If ...
        # - we have no videos yet
        # - we've just added videos
        # - we're currently not public
        # - and we could otherwise be
        # ... make us public
        if not existing_videos and instances and not self.public and self.should_be_public(self, True):
            self.public = True
            self.save()

    def remove_videos(self, video_ids):
        VideoInstance.query.filter_by(channel=self.id).filter(VideoInstance.video.in_(video_ids)).delete(synchronize_session=False)

        # If we shouldn't be public and we are, toggle
        if not self.should_be_public(self, self.public) and self.public:
            self.public = False
            self.save()

    def add_meta(self, locale):
        return ChannelLocaleMeta(channel=self.id, locale=locale).save()


class ChannelLocaleMeta(db.Model):

    __tablename__ = 'channel_locale_meta'
    __table_args__ = (
        UniqueConstraint('locale', 'channel'),
    )

    id = Column(CHAR(24), primary_key=True)
    visible = Column(Boolean(), nullable=False, server_default='true', default=True)
    subscriber_count = Column(Integer, nullable=False, server_default='0', default=0)
    view_count = Column(Integer, nullable=False, server_default='0', default=0)
    star_count = Column(Integer, nullable=False, server_default='0', default=0)
    date_added = Column(DateTime(), nullable=False, default=func.now())
    date_updated = Column(DateTime(), nullable=False, default=func.now(), onupdate=func.now())

    channel = Column(ForeignKey('channel.id'), nullable=False)
    locale = Column(ForeignKey('locale.id'), nullable=False)
    category = Column(ForeignKey('category.id'), nullable=True)

    channel_locale = relationship('Locale', remote_side=[Locale.id], backref='channel_locale_meta')

    def __unicode__(self):
        return self.locale + ' for channel ' + self.channel


class ContentReport(db.Model):
    __tablename__ = 'content_report'
    __table_args__ = (
        UniqueConstraint('object_type', 'object_id', 'reason'),
    )

    id = Column(Integer, primary_key=True)
    date_created = Column(DateTime(), nullable=False, default=func.now())
    object_type = Column(String(16), nullable=False)
    object_id = Column(String(64), nullable=False)
    reason = Column(String(256), nullable=False)
    count = Column(Integer, nullable=False, default=1)
    reviewed = Column(Boolean, nullable=False, default=False)


ParentCategory = aliased(Category)


def _add_es_video(video_instance):
    if not video_instance.video_rel:
        video_instance = VideoInstance.query.get(video_instance.id)
    es_api.add_video_to_index(video_instance)


def _add_es_channel(channel):
    es_api.add_channel_to_index(channel)


def _remove_es_channel(channel):
    es_api.remove_channel_from_index(channel.id)


def _remove_es_video_instance(video_instance):
    es_api.remove_video_from_index(video_instance.id)


@event.listens_for(VideoInstanceLocaleMeta, 'after_update')
def _video_insert(mapper, connection, target):
    _add_es_video(target.video_instance_rel)


@event.listens_for(Video, 'after_update')
def _video_update(mapper, connection, target):
    if not target.visible:
        for i in VideoInstance.query.filter_by(video=target.id):
            _remove_es_video_instance(i)


@event.listens_for(VideoInstance, 'after_insert')
def _video_instance_insert(mapper, connection, target):
    _add_es_video(target)


@event.listens_for(VideoInstance, 'after_update')
def _video_instance_update(mapper, connection, target):
    _remove_es_video_instance(target)


@event.listens_for(VideoInstance, 'after_delete')
def _video_instance_delete(mapper, connection, target):
    _remove_es_video_instance(target)


@event.listens_for(ChannelLocaleMeta, 'after_insert')
def _channel_insert(mapper, connection, target):
    # NOTE: owner_rel isn't available on Channel if we pass channel_rel for owner.resource_url.
    # possibly do a lookup for owner in resource_url method instead of having it rely on self.owner_rel here
    channel = Channel.query.get(target.channel)
    _add_es_channel(channel)


@event.listens_for(ChannelLocaleMeta, 'after_update')
def _es_channel_update_from_clm(mapper, connection, target):
    _add_es_channel(target.channel_rel)


@event.listens_for(Channel, 'after_insert')
def _es_channel_insert_from_channel(mapper, connection, target):
    if target.public:
        _add_es_channel(Channel.query.get(target.id))


@event.listens_for(Channel, 'after_update')
def _es_channel_update_from_channel(mapper, connection, target):
    if not target.public or target.deleted:
        _remove_es_channel(target)
    _add_es_channel(Channel.query.get(target.id))


event.listen(Video, 'before_insert', add_video_pk)
event.listen(VideoInstanceLocaleMeta, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='vl'))
event.listen(VideoInstance, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='vi'))
event.listen(VideoRestriction, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='vr'))
event.listen(VideoThumbnail, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='vt'))
event.listen(Channel, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='ch'))
event.listen(ChannelLocaleMeta, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='cl'))
