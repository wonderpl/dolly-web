from sqlalchemy import (
    Text, String, Column, Boolean, Integer, ForeignKey, DateTime, CHAR,
    UniqueConstraint, event, func)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship, aliased
from rockpack.mainsite.core.dbapi import db
from rockpack.mainsite.helpers.db import (
    add_base64_pk, add_video_pk, add_video_meta_pk,
    insert_new_only, ImageType)
from rockpack.mainsite.helpers.urls import url_for
from rockpack.mainsite.services.user.models import User
from rockpack.mainsite import app
from rockpack.mainsite.core import es


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

    video_instancess = relationship('VideoInstance', backref='category_ref',
                                      passive_deletes=True)
    external_category_maps = relationship('ExternalCategoryMap', backref='category_ref')

    def __unicode__(self):
        parent_name = ''
        if self.parent_category:
            parent_name = self.parent_category.name + ' >'
        return '({}) {} {}'.format(self.locales.name, parent_name, self.name)

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
    date_added = Column(DateTime(), nullable=False, default=func.now())
    date_updated = Column(DateTime(), nullable=False, default=func.now(), onupdate=func.now())
    duration = Column(Integer, nullable=False, server_default='0')
    view_count = Column(Integer, nullable=False, server_default='0')
    star_count = Column(Integer, nullable=False, server_default='0')
    rockpack_curated = Column(Boolean, nullable=False, server_default='false', default=False)
    visible = Column(Boolean(), nullable=False, server_default='true', default=True)

    source = Column(ForeignKey('source.id'), nullable=False)

    thumbnails = relationship('VideoThumbnail', backref='video_rel',
                              lazy='joined', passive_deletes=True,
                              cascade="all, delete-orphan")
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

    @classmethod
    def add_videos(cls, videos, source, locale, channel, category=None):
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

    id = Column(CHAR(40), primary_key=True)

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
    category = Column(ForeignKey('category.id'), nullable=False)

    metas = relationship('VideoInstanceLocaleMeta', backref='video_instance_rel', cascade='all,delete')

    @property
    def default_thumbnail(self):
        return self.video_rel.default_thumbnail

    @property
    def player_link(self):
        return self.video_rel.player_link

    @classmethod
    def add_from_video_ids(cls, video_ids, channel, category, locale):
        """ Bulk add video instances from a list of videos
            and attach meta records """

        session = cls.query.session
        instances = [cls(video=v, channel=channel, category=category) for v in video_ids]
        session.add_all(instances)
        session.commit()

        for i in instances:
            i.metas.append(VideoInstanceLocaleMeta(locale=locale))
            session.add(i)
        session.commit()

    @classmethod
    def remove_from_video_ids(cls, video_ids):
        # Cascading delete
        cls.query.filter(
            cls.video.in_(video_ids)
        ).delete(synchronize_session='fetch')

    def add_meta(self, locale):
        return VideoInstanceLocaleMeta(video_instance=self,
                locale=locale).save()

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
    title = Column(String(1024), nullable=False)
    description = Column(Text, nullable=False)
    cover = Column(ImageType('CHANNEL', reference_only=True), nullable=False)
    public = Column(Boolean(), nullable=False, server_default='true', default=True)
    date_added = Column(DateTime(), nullable=False, default=func.now())
    date_updated = Column(DateTime(), nullable=False, default=func.now(), onupdate=func.now())
    ecommerce_url = Column(String(1024), nullable=False, server_default='')

    category = Column(ForeignKey('category.id'), nullable=True)
    category_rel = relationship(Category, primaryjoin=(category == Category.id), lazy='joined', innerjoin=True)

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
    def channelmeta_for_category(cls, category, locale):
        if locale is None:
            locale = Category.query.filter_by(id=category).value('locale')
        return [ChannelLocaleMeta(
            locale=locale)]

    @classmethod
    def create(cls, locale=None, public=True, **kwargs):
        """Create & save a new channel record along with appropriate category metadata"""
        channel = Channel(**kwargs)
        channel.public = channel.should_be_public(channel, public)
        if kwargs.get('category'):
            channel.metas = cls.channelmeta_for_category(kwargs['category'], locale)
        return channel.save()

    def get_resource_url(self, own=False):
        view = 'userws.owner_channel_info' if own else 'userws.channel_info'
        return url_for(view, userid=self.owner_rel.id, channelid=self.id)

    resource_url = property(get_resource_url)

    def add_videos(self, videos, locale):
        VideoInstance.add_from_video_ids([getattr(v, 'id', v) for v in videos], self.id, self.category, locale)

        instances = [VideoInstance(channel=self.id, video=getattr(v, 'id', v)) for v in videos]
        session = self.query.session
        try:
            with session.begin_nested():
                session.add_all(instances)
        except IntegrityError:
            existing = [i.video for i in session.query(VideoInstance.video).
                        filter_by(channel=self.id).
                        filter(VideoInstance.video.in_(set(i.video for i in instances)))]
            for i in instances:
                if i.video not in existing:
                    session.add_all(i)

    def remove_videos(self, videos):
        VideoInstance.remove_from_video_ids(
            set(
                getattr(v, 'id', v)
                for v in videos.query.filter_by(channel=self.id)))

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


ParentCategory = aliased(Category)


@event.listens_for(Category, 'before_insert')
def _set_child_category_locale(mapper, connection, target):
    if not target.locale and target.parent_category:
        target.locale = target.parent_category.locale


@event.listens_for(VideoInstanceLocaleMeta, 'after_insert')
def _add_video_insert(mapper, connection, target):
    _add_es_video(target.video_instance_rel)


def _locale_dict_from_object(meta):
    return {'view_count': meta.view_count,
            'star_count': meta.star_count}

def _add_es_video(video_instance):
        from rockpack.mainsite.core.es import get_es_connection, api
        conn = get_es_connection()

        locale = {}
        for m in video_instance.metas:
            locale.update({m.locale: _locale_dict_from_object})

        data = dict(
            id=video_instance.id,
            title=video_instance.video_rel.title,
            channel=video_instance.channel,
            category=video_instance.category,
            date_added=video_instance.date_added,
            position=video_instance.position,
            thumbnail_url=video_instance.video_rel.default_thumbnail,
            source=video_instance.video_rel.source,
            source_id=video_instance.video_rel.source_videoid,
            duration=video_instance.video_rel.duration,
            locale=locale)

        print api.add_video_to_index(conn, data)


@event.listens_for(ChannelLocaleMeta, 'after_insert')
def _es_channel_insert(mapper, connection, target):
    # NOTE: owner_rel isn't available on Channel if we pass channel_rel for owner.resource_url.
    # possibly lookup owner in resource_url method instead of having it rely on self.owner_rel
    _add_es_channel(Channel.query.get(target.channel_rel.id), category=target.category)


@event.listens_for(ChannelLocaleMeta, 'after_update')
def _es_channel_update_from_clm(mapper, connection, target):
    _add_es_channel(Channel.query.get(target.channel_rel.id))


@event.listens_for(Channel, 'after_update')
def _es_channel_update_from_channel(mapper, connection, target):
    _add_es_channel(Channel.query.get(target.id))


class MissingChannelInElasticSearch(Exception):
    pass


def _add_es_channel(channel, category=None):
    conn = es.get_es_connection()

    if category:
        category = Category.query.filter(
            Category.parent != None,
            Category.id == category).values('id', 'parent').next()

    locale = {}
    for m in channel.metas:
        locale.update({
            m.locale: {'view_count': m.view_count,
                'star_count': m.star_count}
            })

    data = dict(
        id=channel.id,
        category=category,
        locale=locale,
        owner_id=channel.owner,
        subscribe_count=0,
        description=channel.description,
        resource_url=channel.get_resource_url(),
        title=channel.title,
        thumbnail_url=channel.cover.thumbnail_large,
        cover_thumbnail_small_url=channel.cover.thumbnail_small,
        cover_thumbnail_large_url=channel.cover.thumbnail_large,
        cover_background_url=channel.cover.background)

    print es.api.add_channel_to_index(conn, data)


@event.listens_for(VideoInstance, 'after_delete')
def _es_video_delete(mapper, connection, target):
    es.remove_video_from_index(es.get_es_connection(), target.id)


event.listen(Video, 'before_insert', add_video_pk)
event.listen(VideoInstanceLocaleMeta, 'before_insert', add_video_meta_pk)
event.listen(VideoInstance, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='vi'))
event.listen(VideoRestriction, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='vr'))
event.listen(VideoThumbnail, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='vt'))
event.listen(Channel, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='ch'))
event.listen(ChannelLocaleMeta, 'before_insert', lambda x, y, z: add_base64_pk(x, y, z, prefix='cl'))
