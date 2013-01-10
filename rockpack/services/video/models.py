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
    __tablename__ = 'video_locale'

    id = Column(Integer(), primary_key=True)
    name = Column(String(32))

    def __unicode__(self):
        return self.title


class Category(Base):
    __tablename__ = 'video_category'

    id = Column(Integer(), primary_key=True)
    name = Column(String(32))
    parent_id = Column(ForeignKey('video_category.id'), nullable=True)
    locale_id = Column(ForeignKey('video_locale.id'), nullable=True)
    priority = Column(Integer, default=0)

    def __unicode__(self):
        return self.title


class VideoSource(Base):
    __tablename__ = 'video_videosource'

    id = Column(Integer(), primary_key=True)
    label = Column(String(16))
    player_template = Column(Text)

    def __unicode__(self):
        return self.title


class Video(Base):
    """ Canonical reference to a video """

    __tablename__ = 'video_video'

    id = Column(String(40), primary_key=True)
    title = Column(String(1024), nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    source_id = Column(ForeignKey('video_videosource.id'))
    source_videoid = Column(String(128))
    date_added = Column(TZDateTime(), nullable=False, default=lambda: datetime.now(UTC))
    date_updated = Column(TZDateTime(), nullable=False, default=lambda: datetime.now(UTC))
    locale_id = Column(Integer, ForeignKey('video_locale.id'))
    category_id = Column(Integer, ForeignKey('video_category.id'))
    star_count = Column(Integer, default=0)
    rockpack_curated = Column(Boolean, default=False)

    video_instances = relationship('VideoInstance', backref='video_video')

    def __unicode__(self):
        return self.title


class VideoInstance(Base):
    """ An instance of a video, which can belong to many channels """

    __tablename__ = 'video_videoinstance'

    id = Column(String(40), primary_key=True, default=lambda: make_uuid())
    date_added = Column(TZDateTime(), nullable=False, default=lambda: datetime.now(UTC))
    video_id = Column(String, ForeignKey('video_video.id'))
    channel_id = Column(ForeignKey('video_channel.id'))


class Channel(Base):
    """ A channel, which can contain many videos """

    __tablename__ = 'video_channel'

    id = Column(String(32), primary_key=True, default=lambda: make_uuid())
    title = Column(String(1024))
    thumbnail_url = Column(Text, nullable=True)

    video_instances = relationship('VideoInstance', backref='video_channel')

    def __unicode__(self):
        return self.title


def add_video_pk(mapper, connection, instance):
    """ set up the primary key """
    if not instance.id:
        instance.id = gen_videoid(instance.locale_id, instance.source_id, instance.source_videoid)

event.listen(Video, 'before_insert', add_video_pk)
