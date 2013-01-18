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

    video = relationship('Video', backref='locales')

    def __unicode__(self):
        return self.name

    @classmethod
    def get_form_choices(cls):
        return session.query(cls.id, cls.name)


class Category(Base):

    __tablename__ = 'category'
    __table_args__ = {'mysql_engine': 'InnoDB', }

    id = Column(Integer, primary_key=True)
    name = Column(String(32))
    parent = Column(ForeignKey('category.id'), nullable=True)
    locale = Column(ForeignKey('locale.id'), nullable=True)
    priority = Column(Integer, default=0)

    external_category_maps = relationship('ExternalCategoryMap', backref='video_category')
    video = relationship('Video', backref='categories')

    def __unicode__(self):
        return self.name

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
    locale = Column(ForeignKey('locale.id'))
    category = Column(ForeignKey('category.id'))

    instances = relationship('VideoInstance', backref='videos')
    thumbnails = relationship('VideoThumbnail', backref='videos')
    restrictions = relationship('VideoRestriction', backref='videos')

    def __unicode__(self):
        return self.id

    def __str__(self):
        return self.id

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


class Channel(Base):
    """ A channel, which can contain many videos """

    __tablename__ = 'channel'
    __table_args__ = {'mysql_engine': 'InnoDB', }

    id = Column(String(32), primary_key=True, default=lambda: make_uuid())
    title = Column(String(1024))
    thumbnail_url = Column(Text, nullable=True)
    locale = Column(String(16))
    # user = Column(ForeignKey(models.User))

    video_instances = relationship('VideoInstance', backref='video_channel')

    def __unicode__(self):
        return self.title


ParentCategory = aliased(Category)


def add_video_pk(mapper, connection, instance):
    """ set up the primary key """
    if not instance.id:
        instance.id = gen_videoid(instance.locale, instance.source, instance.source_videoid)


def update_updated_date(mapper, connection, instance):
    if instance.id:
        instance.date_updated = datetime.now(UTC)


event.listen(Video, 'before_insert', add_video_pk)
event.listen(Video, 'before_update', add_video_pk)
