import uuid
from datetime import datetime

from sqlalchemy import (
    Text,
    String,
    Column,
    Boolean,
    Integer,
    ForeignKey,
)

from sqlalchemy import event
from sqlalchemy.orm import relationship

from rockpack.helpers.db import UTC
from rockpack.helpers.db import TZDateTime
from rockpack.core.dbapi import Base

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

    def __unicode__(self):
        return self.name


class Category(Base):

    __tablename__ = 'category'
    __table_args__ = {'mysql_engine': 'InnoDB', }

    id = Column(Integer, primary_key=True)
    name = Column(String(32))
    parent_id = Column(ForeignKey('category.id'), nullable=True)
    locale_id = Column(ForeignKey('locale.id'), nullable=True)
    priority = Column(Integer, default=0)

    external_category_maps = relationship('ExternalCategoryMap', backref='video_category')

    def __unicode__(self):
        return self.name


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

    external_category_maps = relationship('ExternalCategoryMap', backref='video_source')

    def __unicode__(self):
        return self.label


class Video(Base):
    """ Canonical reference to a video """

    __tablename__ = 'video'
    __table_args__ = {'mysql_engine': 'InnoDB', }

    id = Column(String(40), primary_key=True)
    title = Column(String(1024), nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    source_videoid = Column(String(128))
    date_added = Column(TZDateTime(), nullable=False, default=lambda: datetime.now(UTC))
    date_updated = Column(TZDateTime(), nullable=False, default=lambda: datetime.now(UTC))
    star_count = Column(Integer, default=0)
    rockpack_curated = Column(Boolean, default=False)

    source = Column('source', Integer, ForeignKey('source.id'))
    locale = Column('locale', Integer, ForeignKey('locale.id'))
    category = Column('category', Integer, ForeignKey('category.id'))

    instances = relationship('VideoInstance', backref='video_instance')
    thumbmails = relationship('VideoThumbnail', backref='video_thumbnail')

    def __unicode__(self):
        return self.title


class VideoThumbnail(Base):

    __tablename__ = 'video_thumbnail'
    __table_args__ = {'mysql_engine': 'InnoDB', }

    id = Column(Integer, primary_key=True)
    url = Column(String(1024))
    width = Column(Integer)
    height = Column(Integer)
    video = Column(String(40), ForeignKey('video.id'))

    def __unicode__(self):
        return '{}x{} : {}'.format(self.width, self.height, self.url)


class VideoInstance(Base):
    """ An instance of a video, which can belong to many channels """

    __tablename__ = 'video_instance'
    __table_args__ = {'mysql_engine': 'InnoDB', }

    id = Column(String(40), primary_key=True, default=lambda: make_uuid())
    date_added = Column(TZDateTime(), nullable=False, default=lambda: datetime.now(UTC))
    video = Column('video', String(40), ForeignKey('video.id'))
    channel = Column('channel', ForeignKey('channel.id'))

    def __unicode__(self):
        return self.video


class Channel(Base):
    """ A channel, which can contain many videos """

    __tablename__ = 'channel'
    __table_args__ = {'mysql_engine': 'InnoDB', }

    id = Column(String(32), primary_key=True, default=lambda: make_uuid())
    title = Column(String(1024))
    thumbnail_url = Column(Text, nullable=True)

    video_instances = relationship('VideoInstance', backref='video_channel')

    def __unicode__(self):
        return self.title


def add_video_pk(mapper, connection, instance):
    """ set up the primary key """
    if not instance.id:
        instance.id = gen_videoid(instance.locale, instance.source, instance.source_videoid)

event.listen(Video, 'before_insert', add_video_pk)
