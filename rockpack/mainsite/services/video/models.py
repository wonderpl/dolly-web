from datetime import datetime
from sqlalchemy import (
    Text, String, Column, Boolean, Integer, Float, ForeignKey, DateTime, CHAR,
    UniqueConstraint, event, func)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship, aliased, lazyload
from flask.ext.sqlalchemy import models_committed
from rockpack.mainsite.core.dbapi import db, defer_except
from rockpack.mainsite.core.es import use_elasticsearch, api as es_api
from rockpack.mainsite.helpers.db import add_base64_pk, add_video_pk, insert_new_only, ImageType, BoxType
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
        UniqueConstraint('name', 'parent'),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(32), nullable=False)
    parent = Column(ForeignKey('category.id'), nullable=True)
    colour = Column(String(8))

    parent_category = relationship('Category', remote_side=[id], backref='children')
    translations = relationship('CategoryTranslation', backref='category_rel')
    video_instancess = relationship('VideoInstance', backref='category_ref', passive_deletes=True)
    external_category_maps = relationship('ExternalCategoryMap', backref='category_ref')

    def __unicode__(self):
        if self.parent_category:
            return '{} - {}'.format(self.parent_category.name, self.name)
        else:
            return self.name

    @classmethod
    def get_form_choices(cls, locale, children_only=False):
        query = cls.query.filter(
            CategoryTranslation.category == Category.id,
            CategoryTranslation.locale == locale)
        if children_only:
            query = query.filter(Category.parent.isnot(None))
        for category in query.order_by('parent asc'):
            yield category.id, unicode(category)


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


class Mood(db.Model):

    __tablename__ = 'mood'

    id = Column(Integer, primary_key=True)
    name = Column(String(32), nullable=False)


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
        return cls.get_sources().iteritems()

    @classmethod
    def get_sources(cls):
        if not hasattr(cls, '_sources'):
            cls._sources = dict(cls.query.values(cls.id, cls.label))
        return cls._sources

    @classmethod
    def id_to_label(cls, id):
        return cls.get_sources().get(id, id)

    @classmethod
    def label_to_id(cls, label):
        return next((i for i, l in Source.get_sources().iteritems() if l == label), label)


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
    date_published = Column(DateTime(), nullable=False)
    date_added = Column(DateTime(), nullable=False, default=func.now())
    date_updated = Column(DateTime(), nullable=False, default=func.now(), onupdate=func.now())
    duration = Column(Integer, nullable=False, server_default='0')
    view_count = Column(Integer, nullable=False, server_default='0')
    star_count = Column(Integer, nullable=False, server_default='0')
    rockpack_curated = Column(Boolean, nullable=False, server_default='false', default=False)
    visible = Column(Boolean(), nullable=False, server_default='true', default=True)

    link_url = Column(String(2048), nullable=True)
    link_title = Column(String(1024), nullable=True)

    thumbnails = relationship('VideoThumbnail', backref='video_rel',
                              passive_deletes=True,
                              cascade="all, delete-orphan")
    instances = relationship('VideoInstance', backref=db.backref('video_rel', lazy='joined'),
                             passive_deletes=True, cascade="all, delete-orphan")
    restrictions = relationship('VideoRestriction', backref='videos',
                                cascade="all, delete-orphan", passive_deletes=True)

    def __unicode__(self):
        return self.title

    def __repr__(self):
        return 'Video(id={v.id!r}, source_videoid={v.source_videoid!r})'.format(v=self)

    @property
    def source_label(self):
        if not hasattr(self, '_source_label'):
            self._source_label = Source.id_to_label(self.source)
        return self._source_label

    @property
    def default_thumbnail(self):
        # Short-circuit for youtube to avoid join:
        if self.source_label == 'youtube':
            return 'http://i.ytimg.com/vi/%s/mqdefault.jpg' % self.source_videoid
        # TODO: Denormalise this?
        for width, url in sorted((t.width, t.url) for t in self.thumbnails):
            if width >= 320:
                return url

    @property
    def player_link(self):
        if self.source_label == 'youtube':
            return 'http://www.youtube.com/watch?v=' + self.source_videoid
        elif self.source_label == 'ooyala':
            return 'http://player.ooyala.com/iframe.html?options[autoplay]=true&pbid=%s&ec=%s' % (
                app.config['OOYALA_PLAYER_ID'], self.source_videoid)
        else:
            return ''

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


class VideoRestriction(db.Model):

    __tablename__ = 'video_restriction'

    id = Column(CHAR(24), primary_key=True)
    video = Column(ForeignKey('video.id'), nullable=False, index=True)
    relationship = Column(String(16), nullable=False)
    country = Column(String(16), nullable=False)


class VideoThumbnail(db.Model):

    __tablename__ = 'video_thumbnail'

    id = Column(CHAR(24), primary_key=True)
    url = Column(String(1024), nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)

    video = Column(ForeignKey('video.id', ondelete='CASCADE'), nullable=False, index=True)

    def __unicode__(self):
        return '({}x{}) {}'.format(self.width, self.height, self.url)


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
    source_channel = Column(ForeignKey('channel.id'), nullable=True)
    category = Column(ForeignKey('category.id'), nullable=True)
    tags = Column(String(1024), nullable=True)

    metas = relationship('VideoInstanceLocaleMeta', backref='video_instance_rel',
                         cascade='all,delete', passive_deletes=True)
    category_rel = relationship('Category', backref='video_instance_rel')

    def __unicode__(self):
        return self.video

    def __repr__(self):
        return 'VideoInstance(id={v.id!r}, video={v.video!r})'.format(v=self)

    @property
    def default_thumbnail(self):
        return self.video_rel.default_thumbnail

    @property
    def player_link(self):
        return self.video_rel.player_link

    def get_resource_url(self, own=False):
        return url_for('userws.channel_video_instance', userid='-', channelid=self.channel, videoid=self.id)
    resource_url = property(get_resource_url)

    def add_meta(self, locale):
        return VideoInstanceLocaleMeta(video_instance=self.id, locale=locale).save()


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


class VideoInstanceComment(db.Model):

    __tablename__ = 'video_instance_comment'

    id = Column(Integer, primary_key=True)
    video_instance = Column(ForeignKey('video_instance.id', ondelete='CASCADE'), nullable=False)
    user = Column(ForeignKey('user.id'), nullable=False)
    comment = Column(String(120), nullable=False, server_default='')
    date_added = Column(DateTime(), nullable=False, default=func.now())

    user_rel = relationship(User, innerjoin=True)

    def get_resource_url(self, own=False):
        return url_for('userws.video_instance_comment_item',
                       userid='-',
                       channelid='-',
                       videoid=self.video_instance,
                       commentid=self.id)
    resource_url = property(get_resource_url)


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
    date_published = Column(DateTime(), nullable=True)
    update_frequency = Column(Float, nullable=True)
    subscriber_frequency = Column(Float, nullable=True)
    ecommerce_url = Column(String(1024), nullable=False, server_default='')
    editorial_boost = Column(Float(precision=1), nullable=True, server_default='1.0', default=1.0)
    favourite = Column(Boolean(), nullable=False, server_default='false', default=False)

    category = Column(ForeignKey('category.id'), nullable=True)
    category_rel = relationship(Category, primaryjoin=(category == Category.id), lazy='joined')

    owner = Column(CHAR(22), ForeignKey('user.id'), nullable=False, default='', server_default='')
    owner_rel = relationship(User, primaryjoin=(owner == User.id), lazy='joined', innerjoin=True)

    deleted = Column(Boolean(), nullable=False, server_default='false', default=False)
    visible = Column(Boolean(), nullable=False, server_default='True', default=True)

    video_instances = relationship('VideoInstance', backref='video_channel',
                                   foreign_keys=[VideoInstance.__table__.c.channel])
    metas = relationship('ChannelLocaleMeta', backref=db.backref('channel_rel', lazy='joined', innerjoin=True))

    def __unicode__(self):
        return self.title

    def __repr__(self):
        return 'Channel(id={c.id!r}, owner={c.owner!r})'.format(c=self)

    @classmethod
    def get_form_choices(cls, owner):
        return cls.query.filter_by(owner=owner).values(cls.id, cls.title)

    @classmethod
    def create(cls, locale=None, public=True, **kwargs):
        """Create & save a new channel record along with appropriate category metadata"""
        channel = cls(**kwargs)
        channel.public = cls.should_be_public(channel, public, False)
        return channel.save()

    @classmethod
    def should_be_public(self, channel, public, has_instances=None):
        """Return False if conditions for visibility are not met (except for fav channel)"""
        if app.config.get('OVERRIDE_CHANNEL_PUBLIC') or app.config.get('DOLLY'):
            return True
        if channel.favourite:
            return True

        if not (channel.title and channel.cover and channel.category is not None):
            return False
        else:
            if channel.title.upper().startswith(app.config['UNTITLED_CHANNEL'].upper()):
                return False
            if has_instances is None:
                has_instances = VideoInstance.query.filter_by(channel=channel.id).value(func.count())
            if not has_instances:
                return False
            else:
                return public

    @property
    def default_thumbnail(self):
        return self.cover.thumbnail_large

    @property
    def editable(self):
        return not self.favourite

    def get_resource_url(self, own=False):
        view = 'userws.owner_channel_info' if own else 'userws.channel_info'
        return url_for(view, userid=self.owner, channelid=self.id)

    resource_url = property(get_resource_url)

    def add_videos(self, videos, tags=None, date_added=None):
        instances = [VideoInstance(channel=self.id, video=getattr(v, 'id', v),
                                   category=self.category, tags=tags, date_added=date_added) for v in videos]
        existing = dict(VideoInstance.query.filter_by(channel=self.id).values('video', 'id'))
        self.query.session.add_all(i for i in instances if i.video not in existing)

        # If ...
        # - we're currently not public
        # - we have no videos yet
        # - we've just added videos
        # - and we could otherwise be
        # ... make us public
        if not self.public and not existing and instances:
            self.public = Channel.should_be_public(self, True, instances)

        # Get list of instance ids for requested videos
        # XXX: Returning instance here too because id won't be set until after commit
        return [existing[v] for v in videos if v in existing] +\
            [j for j in instances if j.video not in existing]

    def remove_videos(self, video_ids):
        # Instead of bulk deleting by query we get an orm reference for each
        # and delete individually so the ids are recorded for on_models_committed
        videos = VideoInstance.query.\
            options(lazyload('video_rel'), *defer_except(VideoInstance, ['id'])).\
            filter(VideoInstance.channel == self.id, VideoInstance.video.in_(video_ids))
        for video in videos:
            VideoInstance.query.session.delete(video)

    def add_meta(self, locale):
        return ChannelLocaleMeta(channel=self.id, locale=locale).save()

    def promotion_map(self):
        promos = []
        now = datetime.utcnow()
        for p in self.channel_promotion:
            if p.date_start < now and p.date_end > now:
                promos.append(
                    '|'.join([str(p.locale), str(p.category), str(p.position)])
                )
        return promos

    def child_parent_for_category(self):
        category = []
        if self.category:
            if not self.category_rel:
                category = list(Category.query.filter_by(id=self.category).values('id', 'parent').next())
            else:
                category = [self.category_rel.id, self.category_rel.parent]
        return category


class ChannelPromotion(db.Model):
    __tablename__ = 'channel_promotion'

    id = Column(Integer, primary_key=True)
    channel = Column(ForeignKey('channel.id'), nullable=False)
    locale = Column(ForeignKey('locale.id'), nullable=False)
    # Not a real fkey (below). Just an int in the db
    category = Column(ForeignKey('category.id'), nullable=True)
    date_added = Column(DateTime(), nullable=False, default=func.now())
    date_updated = Column(DateTime(), nullable=False, default=func.now(), onupdate=func.now())
    position = Column(Integer, nullable=False)

    date_start = Column(DateTime(), nullable=False, default=func.now())
    date_end = Column(DateTime(), nullable=False, default=func.now())

    channel_rel = relationship('Channel', backref='channel_promotion')
    locale_rel = relationship('Locale', backref='channel_promotion')

    category_rel = relationship(Category, backref='channel_promotion_category',
                                primaryjoin='Category.id==ChannelPromotion.category',
                                foreign_keys=[Category.__table__.c.id])


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
    date_updated = Column(DateTime(), nullable=False, default=func.now(), onupdate=func.now())
    object_type = Column(String(16), nullable=False)
    object_id = Column(String(64), nullable=False)
    reason = Column(String(256), nullable=False)
    count = Column(Integer, nullable=False, default=1)
    reviewed = Column(Boolean, nullable=False, default=False)


class PlayerErrorReport(db.Model):
    __tablename__ = 'player_error'
    __table_args__ = (
        UniqueConstraint('video_instance', 'reason'),
    )

    id = Column(Integer, primary_key=True)
    date_created = Column(DateTime(), nullable=False, default=func.now())
    date_updated = Column(DateTime(), nullable=False, default=func.now(), onupdate=func.now())
    video_instance = Column(ForeignKey('video_instance.id'), nullable=False)
    reason = Column(String(256), nullable=False)
    count = Column(Integer, nullable=False, default=1)


ParentCategory = aliased(Category)


def _channel_is_public(channel):
    return channel.public and channel.visible and not channel.deleted


def _update_or_remove_channel(channel):
    if _channel_is_public(channel):
        es_api.update_channel_to_index(channel)
    else:
        es_api.remove_channel_from_index(channel.id)


# XXX: Do we still need this?
@event.listens_for(VideoInstanceLocaleMeta, 'after_update')
def _video_insert(mapper, connection, target):
    video_instance = target.video_instance_rel
    if not video_instance.video_rel:
        video_instance = VideoInstance.query.get(video_instance.id)
    es_api.add_video_to_index(video_instance)


@event.listens_for(Video, 'after_update')
def _video_update(mapper, connection, target):
    if use_elasticsearch() and not target.visible:
        instance_ids = [x[0] for x in VideoInstance.query.filter_by(video=target.id).values('id')]
        es_api.ESVideo.delete(instance_ids)


@models_committed.connect_via(app)
def on_models_committed(sender, changes):
    updated_videos, deleted_videos = [], []
    for obj, change in changes:
        if isinstance(obj, VideoInstance):
            if change == 'delete':
                deleted_videos.append(obj.id)
            else:
                updated_videos.append(obj.id)
    if updated_videos or deleted_videos:
        es_api.es_update_channel_videos(updated_videos, deleted_videos)


@event.listens_for(ChannelLocaleMeta, 'after_insert')
def _channel_insert(mapper, connection, target):
    # NOTE: owner_rel isn't available on Channel if we pass channel_rel for owner.resource_url.
    # possibly do a lookup for owner in resource_url method instead of having it rely on self.owner_rel here
    channel = Channel.query.get(target.channel)
    if _channel_is_public(channel):
        _update_or_remove_channel(channel)


@event.listens_for(ChannelLocaleMeta, 'after_update')
def _es_channel_update_from_clm(mapper, connection, target):
    _update_or_remove_channel(target.channel_rel)


# XXX: This is called on registration to add user's favourites - needs to move offline
@event.listens_for(Channel, 'after_insert')
def _es_channel_insert_from_channel(mapper, connection, target):
    if _channel_is_public(target):
        es_api.add_channel_to_index(Channel.query.get(target.id))


@event.listens_for(Channel, 'after_update')
def _es_channel_update_from_channel(mapper, connection, target):
    _update_or_remove_channel(target)


@event.listens_for(ChannelPromotion, 'after_insert')
def _es_channel_promotion_insert(mapper, connection, target):
    _update_or_remove_channel(Channel.query.get(target.channel))


@event.listens_for(ChannelPromotion, 'after_update')
def _es_channel_promotion_update(mapper, connection, target):
    _update_or_remove_channel(Channel.query.get(target.channel))


@event.listens_for(Channel, 'before_update')
def _set_date_published(mapper, connection, target):
    if target.public and not target.date_published:
        target.date_published = func.now()


event.listen(Video, 'before_insert', add_video_pk)
event.listen(VideoInstanceLocaleMeta, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='vl'))
event.listen(VideoInstance, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='vi'))
event.listen(VideoRestriction, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='vr'))
event.listen(VideoThumbnail, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='vt'))
event.listen(Channel, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='ch'))
event.listen(ChannelLocaleMeta, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='cl'))
