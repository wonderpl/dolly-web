import logging
import uuid
from datetime import datetime
from sqlalchemy import (
    Text,
    String,
    Column,
    Boolean,
    Integer,
    ForeignKey,
    event
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship, aliased
from rockpack.mainsite.helpers.db import UTC
from rockpack.mainsite.helpers.db import TZDateTime
from rockpack.mainsite.core.dbapi import Base, session



def gen_videoid(locale, source, source_id):
    from base64 import b32encode
    from hashlib import sha1
    prefix = locale.split('-')[1].upper()
    hash = b32encode(sha1(source_id).digest())
    return '%s%06X%s' % (prefix, source, hash)


def make_uuid():
    return uuid.uuid4().hex


class Locale(Base):

    __tablename__ = 'locale'
    __table_args__ = {'mysql_engine': 'InnoDB', }

    id = Column(String(16), primary_key=True)
    name = Column(String(32))

    video_locale_meta = relationship('VideoLocaleMeta', backref='locales')

    def __unicode__(self):
        return ':'.join([self.id, self.name])

    @classmethod
    def get_form_choices(cls):
        return session.query(cls.id, cls.name)


class Category(Base):
    """ Categories for each `locale` """

    __tablename__ = 'category'
    __table_args__ = {'mysql_engine': 'InnoDB',}

    id = Column(Integer, primary_key=True)
    name = Column(String(32))
    priority = Column(Integer, default=0)

    parent = Column(ForeignKey('category.id'), nullable=True)
    locale = Column(ForeignKey('locale.id'))

    parent_category = relationship('Category', remote_side=[id], backref='children')

    video_locale_metas = relationship('VideoLocaleMeta', backref='category_ref')
    locales = relationship('Locale', backref='category_ref')
    channel_locale_metas = relationship('ChannelLocaleMeta', backref='category_ref')
    external_category_maps = relationship('ExternalCategoryMap', backref='category_ref')


    def __unicode__(self):
        parent = ''
        if self.parent_category:
            parent = self.parent_category.name
        r = ':'.join([parent, self.name, self.locale])
        return r


class CategoryMap(Base):
    """ Mapping between localised categories """

    __tablename__ = 'category_locale'
    __table_args__ = {'mysql_engine': 'InnoDB', }

    id = Column(Integer, primary_key=True)

    here = Column(ForeignKey('category.id'))
    there = Column(ForeignKey('category.id'))

    category_here = relationship('Category', foreign_keys=[here])
    category_there = relationship('Category', foreign_keys=[there])

    def __unicode__(self):
        return '{} translates to {}'.format(
                ':'.join([self.here.name, self.here.locale]),
                ':'.join([self.there.name, self.there.locale]),
                )

    @classmethod
    def get_form_choices(cls, locale):
        query = session.query(cls.id, cls.name, ParentCategory.name).\
            filter(cls.parent == ParentCategory.id).\
            filter(cls.locale == locale)
        for id, name, parent in query:
            yield id, '%s - %s' % (parent, name)


class ExternalCategoryMap(Base):

    __tablename__ = 'external_category_map'
    __table_args__ = {'mysql_engine': 'InnoDB', }

    id = Column(Integer, primary_key=True)
    term = Column(String(32))
    label = Column(String(64), nullable=True)
    locale = Column(String(16), ForeignKey('locale.id'))
    category = Column(Integer, ForeignKey('category.id'))
    source = Column(Integer, ForeignKey('source.id'))


class Source(Base):
    __tablename__ = 'source'
    __table_args__ = {'mysql_engine': 'InnoDB', }

    id = Column(Integer(), primary_key=True)
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
    __table_args__ = {'mysql_engine': 'InnoDB', }

    id = Column(String(40), primary_key=True)
    title = Column(String(1024), nullable=True)
    source_videoid = Column(String(128))
    source_listid = Column(String(128), nullable=True)
    date_added = Column(TZDateTime(), nullable=False, default=lambda: datetime.now(UTC))
    date_updated = Column(TZDateTime(), nullable=False, default=lambda: datetime.now(UTC))
    duration = Column(Integer, default=0)
    star_count = Column(Integer, default=0)
    rockpack_curated = Column(Boolean, default=False)

    source = Column(ForeignKey('source.id'))

    thumbnails = relationship('VideoThumbnail', backref='video_rel')
    metas = relationship('VideoLocaleMeta', backref='video_rel')
    instances = relationship('VideoInstance', backref='video_rel')
    restrictions = relationship('VideoRestriction', backref='videos')


    def __str__(self):
        return self.title

    @classmethod
    def add_videos(cls, videos, source, locale, category):
        count = 0
        for video in videos:
            video.source = source
            video.locale = locale
            video.category = category
            try:
                session.add(video)
            except IntegrityError, e:
                # Video already exists.  XXX: Need to check column?
                logging.warning(e)
            else:
                count += 1
        session.commit()
        return count


class VideoLocaleMeta(Base):

    __tablename__ = 'video_locale_meta'
    __table_args__ = {'mysql_engine': 'InnoDB', }

    id = Column(Integer, primary_key=True)

    video = Column(String(40), ForeignKey('video.id'))
    locale = Column(ForeignKey('locale.id'))
    category = Column(ForeignKey('category.id'))
    star_count = Column(Integer, default=0)


class VideoRestriction(Base):

    __tablename__ = 'video_restriction'

    id = Column(Integer, primary_key=True)
    video = Column(String(40), ForeignKey('video.id'))
    relationship = Column(String(16))
    country = Column(String(8))


class VideoInstance(Base):
    """ An instance of a video, which can belong to many channels """

    __tablename__ = 'video_instance'
    __table_args__ = {'mysql_engine': 'InnoDB', }

    id = Column(String(40), primary_key=True, default=lambda: make_uuid())
    date_added = Column(TZDateTime(), nullable=False, default=lambda: datetime.now(UTC))

    video = Column(String(40), ForeignKey('video.id'))
    channel = Column(String(32), ForeignKey('channel.id'))

    def __unicode__(self):
        return self.video

class VideoThumbnail(Base):

    __tablename__ = 'video_thumbnail'
    __table_args__ = {'mysql_engine': 'InnoDB', }

    id = Column(Integer, primary_key=True)
    url = Column(String(1024))
    width = Column(Integer)
    height = Column(Integer)

    video = Column(String(40), ForeignKey('video.id'))

    def __unicode__(self):
        return '({}x{}) {}'.format(self.width, self.height, self.url)


class Channel(Base):
    """ A channel, which can contain many videos """

    __tablename__ = 'channel'
    __table_args__ = {'mysql_engine': 'InnoDB', }

    id = Column(String(32), primary_key=True, default=lambda: make_uuid())
    title = Column(String(1024))
    thumbnail_url = Column(Text, nullable=True)

    video_instances = relationship('VideoInstance', backref='video_channel')
    channel_locale_metas = relationship('ChannelLocaleMeta', backref='meta_parent')

    def __unicode__(self):
        return self.title


class ChannelLocaleMeta(Base):

    __tablename__ = 'channel_locale_meta'
    __table_args__ = {'mysql_engine': 'InnoDB', }

    id = Column(Integer, primary_key=True)

    channel = Column(ForeignKey('channel.id'))
    locale = Column(ForeignKey('locale.id'))
    category = Column(ForeignKey('category.id'), nullable=True)

    channel_locale = relationship('Locale', remote_side=[Locale.id], backref='channel_locale_meta')

    def __unicode__(self):
        return self.locale, 'for channel', self.channel


ParentCategory = aliased(Category)


def add_video_pk(mapper, connection, instance):
    """ set up the primary key """
    if not instance.id:
        instance.id = gen_videoid('is-p', instance.source, instance.source_videoid)

def add_video_instance_pk(mapper, connection, instance):
    if not instance.id:
        instance.id = gen_videoid(instance.locale, instance.source, instance.source_videoid)


def update_updated_date(mapper, connection, instance):
    if instance.id:
        instance.date_updated = datetime.now(UTC)


event.listen(Video, 'before_insert', add_video_pk)
