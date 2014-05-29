from datetime import datetime
from flask import json
from sqlalchemy import (
    Text, String, Column, Boolean, Integer, Float, ForeignKey, DateTime, CHAR,
    UniqueConstraint, event, func)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship, aliased, lazyload
from sqlalchemy.orm.attributes import get_history
from rockpack.mainsite import app, cache
from rockpack.mainsite.core.dbapi import db, defer_except, commit_on_success
from rockpack.mainsite.helpers import lazy_gettext as _
from rockpack.mainsite.helpers.db import add_base64_pk, add_video_pk, insert_new_only, ImageType, BoxType
from rockpack.mainsite.helpers.urls import url_for
from rockpack.mainsite.services.user.models import User
from rockpack.mainsite.background_sqs_processor import background_on_sqs


EXTRA_META_KEYWORD = 'EXTRA_META'


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

    @classmethod
    @cache.memoize(300)
    def get_colour_map(cls):
        colour = func.coalesce(Category.colour, ParentCategory.colour)
        return dict(
            Category.query.outerjoin(
                ParentCategory, ParentCategory.id == Category.parent
            ).filter(colour.isnot(None)).values(Category.id, colour)
        )


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
    display_name = Column(String(32), nullable=False)


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
    @cache.memoize(3600)
    def get_sources(cls):
        return dict(cls.query.values(cls.id, cls.label))

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
    category = Column(ForeignKey('category.id'), nullable=True)
    description = Column(Text)
    link_url = Column(String(2048), nullable=True)
    link_title = Column(String(1024), nullable=True)

    category_rel = relationship('Category', backref='video_rel')
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

    @staticmethod
    def extra_meta(video):
        """ Parses out a list of dicts from a string
            following the EXTRA_META_KEYWORD tag """

        if not video.description:
            return {}

        sm = video.description.split(EXTRA_META_KEYWORD, 1)

        if len(sm) > 1:
            lines = []
            for line in sm[1].split('\n'):
                lines.append(line.strip())

            try:
                return json.loads(''.join(lines))
            except:
                app.logger.error('Failed to load extra_meta for video %s', str(video.id))
        return {}

    @staticmethod
    def cleaned_description(description):
        if not description:
            return ''
        return description.split(EXTRA_META_KEYWORD, 1)[0] if description else ''

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
    date_tagged = Column(DateTime())
    date_updated = Column(DateTime(), nullable=False, default=func.now(), onupdate=func.now())
    video = Column(ForeignKey('video.id', ondelete='CASCADE'), nullable=False)
    channel = Column(ForeignKey('channel.id'), nullable=False)
    source_channel = Column(ForeignKey('channel.id'), nullable=True)
    original_channel_owner = Column(ForeignKey('user.id'), nullable=True)
    category = Column(ForeignKey('category.id'), nullable=True)
    tags = Column(String(1024), nullable=True)
    is_favourite = Column(Boolean(), nullable=False, server_default='false', default=False)
    deleted = Column(Boolean(), nullable=False, server_default='false', default=False)
    most_influential = Column(Boolean(), nullable=False, server_default='false', default=False)

    metas = relationship('VideoInstanceLocaleMeta', backref='video_instance_rel',
                         cascade='all,delete', passive_deletes=True)
    category_rel = relationship('Category', backref='video_instance_rel')
    original_channel_owner_rel = relationship('User', backref='video_instance_rel')

    def __unicode__(self):
        return self.id or u'new'

    def __repr__(self):
        return 'VideoInstance(id={v.id!r}, video={v.video!r})'.format(v=self)

    @property
    def label(self):
        labels = self.tags and [t[6:] for t in self.tags.split(',') if t.startswith('label-')]
        if labels:
            label = labels[0].replace('-', ' ')
            return label.capitalize() if label.islower() else label
        elif not self.original_channel_owner:
            return _('Latest')

    @property
    def default_thumbnail(self):
        return self.video_rel.default_thumbnail

    @property
    def player_link(self):
        return self.video_rel.player_link

    def get_resource_url(self, own=False):
        return url_for('userws.channel_video_instance', userid='-', channelid=self.channel, videoid=self.id)

    resource_url = property(get_resource_url)

    def get_original_channel_owner(self):
        if self.original_channel_owner and self.original_channel_owner_rel.is_active:
            return self.original_channel_owner_rel

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
    video_instance_rel = relationship('VideoInstance',
                                      backref=db.backref('videoinstancecomments',
                                                         passive_deletes=True,
                                                         cascade="all, delete-orphan"))

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
        if self.owner_rel:
            return u'{}, {}'.format(self.owner_rel.username, self.title)
        else:
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
                has_instances = channel.video_count > 0
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

    @property
    def video_count(self):
        if not hasattr(self, '_video_count'):
            self._video_count = VideoInstance.query.join(
                Video,
                (Video.id == VideoInstance.video) &
                (Video.visible == True)
            ).filter(VideoInstance.channel == self.id).value(func.count())
        return self._video_count

    @property
    def category_colour(self):
        return Category.get_colour_map().get(self.category)

    def get_resource_url(self, own=False):
        view = 'userws.owner_channel_info' if own else 'userws.channel_info'
        return url_for(view, userid=self.owner, channelid=self.id)

    resource_url = property(get_resource_url)

    def set_cover_fallback(self, videos):
        if not self.cover and videos and app.config.get('DOLLY'):
            try:
                try:
                    first = videos[0]
                except (AttributeError, TypeError):
                    return
                if isinstance(first, basestring):
                    first = Video.query.get(first)
                self.cover = first.default_thumbnail
            except Exception:
                app.logger.exception('Unable to set cover from video: %s', self.id)

    def add_videos(self, videos, tags=None, category=None, date_added=None):
        instances = [
            VideoInstance(
                channel=self.id,
                video=getattr(v, 'id', v),
                category=category or self.category,
                tags=tags,
                date_added=date_added,
                is_favourite=self.favourite
            )
            for v in videos
        ]
        existing = dict(VideoInstance.query.filter_by(channel=self.id).values('video', 'id'))
        self.query.session.add_all(i for i in instances if i.video not in existing)

        self.set_cover_fallback(videos)

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
            video.deleted = True

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


class UserPromotion(db.Model):
    __tablename__ = 'user_promotion'

    id = Column(Integer, primary_key=True)
    position = Column(Integer, nullable=False)

    date_added = Column(DateTime(), nullable=False, default=func.now())
    date_updated = Column(DateTime(), nullable=False, default=func.now(), onupdate=func.now())
    date_start = Column(DateTime(), nullable=False, default=func.now())
    date_end = Column(DateTime(), nullable=False, default=func.now())

    # NOTE: Not a real fkey (category_id). Just an int in the db
    category_id = Column('category', ForeignKey('category.id'), nullable=True)
    user_id = Column('user', ForeignKey('user.id'), nullable=False)
    locale_id = Column('locale', ForeignKey('locale.id'), nullable=False)

    category = relationship(Category, backref='user_promotion_category',
                            primaryjoin='Category.id==UserPromotion.category_id',
                            foreign_keys=[Category.__table__.c.id])
    user = relationship('User', backref='user_promotion')
    locale = relationship('Locale', backref='user_promotion')


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


class VideoInstanceQueue(db.Model):
    __tablename__ = 'video_instance_queue'

    id = Column(Integer, primary_key=True)
    date_scheduled = Column(DateTime(), nullable=False)
    source_instance = Column(ForeignKey('video_instance.id'), nullable=False)
    target_channel = Column(ForeignKey('channel.id'), nullable=False)
    new_instance = Column(ForeignKey('video_instance.id'))
    tags = Column(String(1024), nullable=True)

    source_instance_rel = relationship('VideoInstance', foreign_keys=[source_instance], lazy='joined')
    target_channel_rel = relationship('Channel')


ParentCategory = aliased(Category)


def _channel_is_public(channel):
    return channel.public and channel.visible and not channel.deleted


@background_on_sqs
def _update_or_remove_channel(channelid):
    channel = Channel.query.get(channelid)
    if channel is not None:
        # Explicit check for push subscriptions if channel deleted
        if channel.deleted:
            from rockpack.mainsite.services.pubsubhubbub.models import Subscription
            Subscription.query.filter(Subscription.channel_id == channel.id).delete()


@background_on_sqs
@commit_on_success
def _update_channel_category(channelids):
    from rockpack.mainsite.core.es.update import update_potential_categories, _category_channel_mapping
    for channelid in channelids:
        category_map = _category_channel_mapping([channelid])
        update_potential_categories(channelid, category_map)


@background_on_sqs
@commit_on_success
def update_video_instance_date_updated(instance_ids, visible=None):
    instances = VideoInstance.query.filter(VideoInstance.id.in_(instance_ids))
    for instance in instances:
        instance.date_updated = datetime.utcnow()
        if visible is not None:
            instance.deleted = not visible


@background_on_sqs
@commit_on_success
def update_channel_date_updated(channel_ids):
    channels = Channel.query.filter(Channel.id.in_(channel_ids))
    for channel in channels:
        channel.date_updated = datetime.now()


def get_influential_instances(video_ids=None, instance_ids=None):
    child = aliased(VideoInstance, name='child')
    query = db.session.query(
        VideoInstance.id,
        VideoInstance.video,
        VideoInstance.is_favourite,
        child.source_channel,
        func.count(VideoInstance.id)
    ).outerjoin(
        child,
        (VideoInstance.video == child.video) &
        (VideoInstance.channel == child.source_channel)
    ).join(
        Video,
        (Video.id == VideoInstance.video) &
        (Video.visible == True)
    ).join(
        Channel,
        (Channel.id == VideoInstance.channel) &
        (Channel.deleted == False) &
        (Channel.public == True)
    ).group_by(VideoInstance.id, VideoInstance.video,
               VideoInstance.is_favourite, child.source_channel)

    if video_ids is not None:
        query = query.filter(VideoInstance.video.in_(video_ids))

    if instance_ids is not None:
        query = query.filter(VideoInstance.id.in_(instance_ids))

    return query


def get_influential_count_by_instance(instance_id):
    """ returns _id, video, fav, source_channel, count """
    result = list(get_influential_instances(instance_ids=[instance_id]))
    if result:
        return result[0]


@background_on_sqs
@commit_on_success
def _update_most_influential(instance_id):
    """ Calculate the most influential instance related
        to this instance.

        Otherwise, get the influential counts from the instance
        that this was "repinned" from, compare counts to the existing
        most influential and update repinned instance if it has more """

    instance = VideoInstance.query.get(instance_id)

    source_instance = VideoInstance.query.filter(
        VideoInstance.video == instance.video,
        VideoInstance.channel == instance.source_channel).first()

    most_influential_instance = VideoInstance.query.filter(
        VideoInstance.most_influential == True,
        VideoInstance.video == instance.video).first()

    if not source_instance and not most_influential_instance:
        # This must be the first instance for that video.
        # Set as most influential
        instance.most_influential == True
        return

    elif most_influential_instance \
            and most_influential_instance.id == instance.id:
        # Are we processing this again?
        # If we are then lets just exit
        return

    source_id, source_video, source_is_fav, source_source_channel, source_count = get_influential_count_by_instance(source_instance.id)

    if not most_influential_instance:
        # If we don't have a most influential for this video
        source_instance.most_influential == True
    elif most_influential_instance.is_favourite:
        # If the existing influential instance is a fav
        # then switch to the new one instead
        source_instance.most_influential == True
        most_influential_instance.most_influential == False
    else:
        _, _, _, _, current_influential_count = get_influential_count_by_instance(most_influential_instance.id)

        if source_count > current_influential_count:
            source_instance.most_influential == True
            most_influential_instance.most_influential == False


@event.listens_for(VideoInstance, 'after_insert')
def video_instance_change(mapper, connection, target):
    if app.config.get('DOLLY'):
        _update_channel_category([target.channel])
        _update_most_influential(target.id)


@event.listens_for(VideoInstance, 'after_update')
def video_instance_update(mapper, connection, target):
    if app.config.get('DOLLY') and target.deleted:
        _update_channel_category([target.channel])


@event.listens_for(Channel, 'before_update')
def _set_date_published(mapper, connection, target):
    if target.public and not target.date_published:
        target.date_published = func.now()


@event.listens_for(Channel, 'before_update')
def check_channel_visibility(mapper, connection, target):
    """ Put channel.public to False if the other flags
        would suggest it should be """
    if target.public:
        if not target.visible or target.deleted:
            target.public = False


@event.listens_for(Channel, 'after_update')
def channel_visibility_change(mapper, connection, target):
    if (get_history(target, 'public').has_changes() or
        get_history(target, 'deleted').has_changes() or
            get_history(target, 'visible').has_changes()):

        instances = VideoInstance.query.filter(VideoInstance.channel == target.id).values('id')
        update_video_instance_date_updated([i[0] for i in instances], visible=_channel_is_public(target))


@event.listens_for(VideoInstance, 'before_insert')
def _auto_tag(mapper, connection, target):
    tag = app.config.get('AUTO_TAG_CHANNELS', {}).get(target.channel)
    if tag and target.source_channel:
        # use background function so we're not messing around in this transaction
        _set_auto_tag(target.source_channel, target.video, tag)


@event.listens_for(ChannelLocaleMeta, 'after_update')
def channel_date_update_trigger_from_meta(mapper, connection, target):
    update_channel_date_updated([target.channel_rel.id])


@event.listens_for(VideoInstanceLocaleMeta, 'after_update')
def video_instance_date_update_trigger_from_meta(mapper, connection, target):
    update_video_instance_date_updated([target.video_instance_rel.id])


@event.listens_for(Video, 'after_update')
def video_instance_date_update_trigger_from_video(mapper, connection, target):
    instances = VideoInstance.query.filter(VideoInstance.video == target.id).values('id')
    update_video_instance_date_updated([i[0] for i in instances], visible=target.visible)


@background_on_sqs
def _set_auto_tag(channel, video, tag):
    instance = VideoInstance.query.filter_by(channel=channel, video=video).first()
    if instance:
        if instance.tags:
            instance.tags += ',' + tag
        else:
            instance.tags = tag
        instance.save()


@event.listens_for(VideoInstance, 'before_update')
@event.listens_for(VideoInstance, 'before_insert')
def _set_date_tagged(mapper, connection, target):
    if target.tags and get_history(target, 'tags').has_changes():
        target.date_tagged = func.now()


event.listen(Video, 'before_insert', add_video_pk)
event.listen(VideoInstanceLocaleMeta, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='vl'))
event.listen(VideoInstance, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='vi'))
event.listen(VideoRestriction, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='vr'))
event.listen(VideoThumbnail, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='vt'))
event.listen(Channel, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='ch'))
event.listen(ChannelLocaleMeta, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='cl'))
